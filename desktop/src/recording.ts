type Item = Record<string, any>;

// Both the stop button and global controls use this merge. Inputs stay untouched
// so undo, the original draft and an interrupted recording remain recoverable.
export function replaceRecordedSteps(original: Item, ids: string[], captured: Item): Item {
  const selected = original.steps.map((s: Item, i: number) => ids.includes(s.id) ? i : -1).filter((i: number) => i >= 0);
  if (!selected.length || selected.length !== ids.length || selected.some((n: number, i: number) => n !== selected[0] + i)) {
    throw Error('重录需要选择连续步骤');
  }
  if (!captured.steps.length) throw Error('没有捕获到步骤，原步骤已保留');
  const next = structuredClone(original), at = selected[0];
  next.schema = 'bokkio.runtime-workflow.v2';
  const aliases: Record<string, string> = {};
  for (const [alias, app] of Object.entries(captured.apps)) {
    let name = 'recorded_' + alias, suffix = 1;
    while (Object.hasOwn(next.apps, name)) name = 'recorded_' + alias + '_' + suffix++;
    next.apps[name] = structuredClone(app); aliases[alias] = name;
  }
  const start = original.steps[at].recorded_at ?? 0;
  const first = captured.steps[0].recorded_at ?? 0;
  const replacements = captured.steps.map((s: Item, i: number) => ({
    ...structuredClone(s), id: i === 0 ? original.steps[at].id : s.id,
    app: aliases[s.app], recorded_at: start + Math.max(0, (s.recorded_at ?? first) - first),
    ...(i === 0 ? {breakpoint: !!original.steps[at].breakpoint, enabled: original.steps[at].enabled !== false} : {})
  }));
  const delta = replacements.at(-1).recorded_at - (original.steps[at + ids.length - 1].recorded_at ?? start);
  next.steps.splice(at, ids.length, ...replacements);
  for (const s of next.steps.slice(at + replacements.length)) {
    if (typeof s.recorded_at === 'number') s.recorded_at = Math.max(0, s.recorded_at + delta);
  }
  return next;
}

export function updateRecordedStep(current: Item, patch: Item): Item {
  const next = {...structuredClone(current), ...structuredClone(patch)};
  if (patch.target && ['role', 'name', 'ancestors'].some(k => JSON.stringify(patch.target[k]) !== JSON.stringify(current.target?.[k]))) {
    delete next.target.native_selector;
  }
  if (patch.window !== undefined && patch.window !== current.window) {
    delete next.window_context;
    for (const ancestor of [...(next.target?.ancestors || []), ...(next.target?.native_selector?.ancestors || [])]) {
      if (['window', 'dialog', 'AXWindow', 'AXSheet'].includes(ancestor.role) && ancestor.name === current.window) ancestor.name = patch.window;
    }
    if (['window', 'dialog'].includes(next.target?.role) && next.target.name === current.window) next.target.name = patch.window;
  }
  if (patch.arguments?.value !== undefined && ['set_value', 'replace_text', 'type'].includes(current.action)) {
    for (const check of next.verify || []) {
      if (check.field === 'value' && check.role === current.target?.role && check.name === current.target?.name && check.equals === current.arguments?.value) check.equals = patch.arguments.value;
    }
  }
  return next;
}
