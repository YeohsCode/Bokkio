"""Fixed robustness fixtures derived from WAA tasks, not official WAA inputs.

Setup and independent expectations never become planner observations. Only the
task instruction and native UI are available during execution.
"""
from pathlib import Path


VARIANTS = {
    'png-spaces': 'png-list',
    'png-many': 'png-list',
    'size-boundary': 'size-report',
    'size-many': 'size-report',
    'count-punctuation': 'word-count',
    'count-zero': 'word-count',
}


def prepare_variant(variant, source):
    """Create only source inputs; return an instruction and hidden expectation."""
    case = VARIANTS[variant]
    if case == 'png-list':
        names = (['alpha image.png', 'release final.PNG', 'zeta.png',
                  'ignore.png.txt', 'readme.txt', 'preview.jpg'] if variant == 'png-spaces'
                 else [f'picture {n:02}.png' for n in range(1, 11)] + ['other.jpg', 'notes.txt'])
        for name in names:
            # Explorer only enumerates these fixtures; their bytes are not images.
            (source / name).write_bytes(b'Enumeration fixture\n')
        expected = [n for n in names if Path(n).suffix.lower() == '.png']
        instruction = ('First use the native Explorer View menu to show file name extensions, '
                       'then observe the full file names. List all file names with a .png extension in the Pictures folder, '
                       'case-insensitively, including their extensions. Write exactly one '
                       'name per line in Notepad, with no headings or extra text.')
    elif case == 'size-report':
        mib = 1024 * 1024
        sizes = ({'below limit.bin': 4*mib, 'exact limit.bin': 5*mib,
                  'above limit.bin': 6*mib, 'small.txt': 1200} if variant == 'size-boundary'
                 else {'archive one.bin': 7*mib, 'archive two.bin': 9*mib,
                       'archive three.bin': 12*mib, 'small.dat': 2*mib})
        for name, size in sizes.items():
            with (source / name).open('wb') as file:
                file.truncate(size)
        expected = [n for n, size in sizes.items() if size > 5*mib]
        instruction = ('List file names in the Downloads folder whose sizes are strictly '
                       'greater than 5 MiB (5,120 KB). Exclude files equal to that limit. '
                       'Include extensions; write one name per line in Notepad with no '
                       'headings or extra text.')
    else:
        content, expected = (
            ('example, EXAMPLE! Example? (example) example; example\nexample.\n'
             'Distractors: examples counterexample preexample.\n', '7')
            if variant == 'count-punctuation' else
            ('There are examples, counterexample and preexample.\n'
             'No standalone matching word occurs here.\n', '0'))
        (source / 'largefile.txt').write_text(content, encoding='utf-8')
        instruction = ('Open "largefile.txt" from the Documents folder in Notepad. '
                       'Count the word "example" as a whole word, case-insensitively; '
                       'punctuation separates words, substrings in other words do not count. '
                       'Write only the decimal count in Notepad, with no extra text.')
    return sorted(source.iterdir()), instruction, expected


def evaluate_variant(case, artifact, expected):
    """Independent post-run oracle; reject duplicate or additional output lines."""
    if not artifact.is_file():
        return False
    actual = artifact.read_text(encoding='utf-8-sig').replace('\r\n', '\n')
    if case == 'word-count':
        return actual.strip() == expected
    lines = actual.splitlines()
    return len(lines) == len(expected) and set(lines) == set(expected)
