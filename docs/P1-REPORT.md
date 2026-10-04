# P1 Report: macOS AX Read Layer

Date: 2026-10-01

Runtime: `xa11y==0.15.0` Python wheel, macOS 15.5, Apple Silicon.

## Result

Live macOS reads now work. The latest CLI run enumerated 35 applications and read TextEdit, Finder, System Settings, the fixed Cocoa application, and Safari through native Accessibility. `find`, `get`, window enumeration, and selection by full window ref were verified. Finder ref sets stayed unchanged in the latest three measured snapshot pairs despite changing label text. Structural changes still require refreshed snapshots.

The 2026-09-28 attempt failed with Accessibility denial. On 2026-10-01 the user approved enabling Accessibility for ChatGPT and the exact uv Python executable. The Python entry and ChatGPT switch were verified on. Full window content was readable without adding Python Screen Recording permission.

## Live matrix

Node counts include application roots and OS-provided sharing dialogs where exposed. These are samples of the current app state, not fixed capability limits. Timings include two complete CLI process launches and snapshots, for all rows in this follow-up matrix.

| Application | Nodes | Unique refs | Same ref set across two reads | Raw read errors | Two reads |
|---|---:|---|---|---:|---:|
| TextEdit | 51 | Yes | Yes | 0 | 2.128 s |
| Finder | 3,110 | Yes | Yes: 13 names changed at common refs | 0 | 6.756 s |
| System Settings | 184 | Yes | Yes | 0 | 2.379 s |
| BokkioTest | 92 | Yes | Yes | 0 | 2.166 s |
| Safari, local form | 47 | Yes | Yes | 0 | 2.229 s |

TextEdit exposes document text areas and formatting controls, but 18 nodes normalize to `unknown`. System Settings exposes lists, cells, and permission switches. Finder exposes a large native tree: 1,107 table cells, 876 static texts, and 265 text fields in this sample. The fixed app exposes native buttons, input fields, combo box, and selectable table rows.

Safari's local form exposed `Test name` as a text field, `Test submit` as a button, and `Test option` as a combo box through AX. It is a compatibility sample for Computer Use. No DOM adapter was used.

The initial ref algorithm lost 10–14 static-text refs in separate Finder pairs. Each changed label was the only static-text child under its unchanged parent and had no native stable ID. Its text was included in its ref path, so a value change invalidated its identity.

`structural-v2` omits the name only for a single non-clickable static-text child. Interactive names and names needed to distinguish multiple text siblings remain part of identity. Three subsequent Finder pairs each contained 3,110 nodes and had zero removed/added refs. Their common-ref name changes were 8, 15, and 13; bounds changes were 293, 295, and 276. These measurements demonstrate stability under this label churn, not persistent semantic identity after sorting, virtualization, or element replacement.

## Defects found by live testing

1. A real xa11y `App` has no element `role` or `raw` properties. Traversal now starts from `App.as_element()` and application metadata reports role `application`.
2. `Element.raw` is a property. It was previously called as a function, hiding provider attributes behind `read_error`. It is now read as a property; live raw read errors are zero in the main matrix.
3. Native stable IDs such as `_NS:8` can repeat across distinct TextEdit windows. xa11y's window list lost distinct windows in this sample. Bokkio now enumerates window/dialog nodes from the application tree and uses structural refs consistently for window listing, snapshots, and lookup.

The test doubles now mirror the real `App.as_element()` boundary and include repeated native window IDs. These cases previously passed fake tests while failing on a real desktop.

## Element contract and mapping

| Public field | Source |
|---|---|
| `ref` | SHA-256 prefix of app PID/name and structural role/name/occurrence path; unique passive labels omit name |
| `platform` | `macos` on this host |
| `role`, `name`, `value`, `bounds` | xa11y element properties |
| `state` | xa11y enabled/visible/focused/selected and related state properties |
| `parent`, `children` | Application-root traversal and refs |
| `actions` | Normalized native verbs plus directional scroll for numeric macOS scroll bars |
| `platform_data` | Raw AX map, description, original actions, native stable ID, and scroll-bar numeric value |

The snapshot wrapper labels this ref policy as `ref_strategy: "structural-v2"`. Old snapshots must be refreshed after the algorithm change.

Missing values are explicit `null` or empty structures. JSON snapshots contain `app`, `window_filter`, and `windows`; without a filter, `windows` holds the application-root tree. Selected window roots have `parent: null`, retaining the same ref as the app tree.

Refs remain stable when application identity and role/name/occurrence paths remain stable. They can change after app restart, interactive renaming, text-sibling count changes, or sibling reordering. They are not persistent identities across launches. `get` requires a new snapshot when a ref disappears. P2 actions return structured stale/ambiguous/mismatched selector errors.

## Evidence and reproduction

- [Summary and application matrix](evidence/2026-10-01-followup/summary.json)
- [Blank TextEdit window](evidence/2026-10-01-followup/textedit-blank.json)
- [Native fixture snapshot](evidence/2026-10-01-followup/fixture.json)
- [Finder stability analysis](evidence/2026-10-01-followup/finder-stability.json)
- [Initial baseline and Safari controls](evidence/2026-10-01/README.md)

Only the blank TextEdit window and disposable native fixture have full raw snapshots saved. Other application evidence contains aggregate counts and roles.

The live harness is `scripts/verify_native.py`. It checks unique refs, valid parents, raw data, lookup, window-ref consistency, and three native action sequences. Fixture setup is in [the evidence guide](evidence/2026-10-01-followup/README.md).

## Remaining limitations

Refs after structural changes and unknown roles still need broader coverage. Menus, virtualized controls, and long-lived references across window recreation need broader coverage. Windows UIA is unverified. Directional macOS scrolling through exposed numeric scroll bars now passes live tests; containers without these bars remain unsupported. Native results are documented in [P2](P2-REPORT.md).
