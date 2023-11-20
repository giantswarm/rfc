#!/usr/bin/env python3
# This checks the required RFC file format as described in https://github.com/giantswarm/rfc/tree/main/decision-process.
# Also, for the purpose of rendering RFCs in our https://github.com/giantswarm/handbook, this script can output all RFCs
# in a stable JSON format to a file so that the rendering script can use that information instead of writing the
# parsing code twice.
import argparse
import datetime
import difflib
import json
import os
import re
import sys

import frontmatter
import yaml  # used by frontmatter, so we can use exception types from here


class RfcFormatProblems(RuntimeError):
    def __init__(self, problems):
        self.problems = problems


ALLOWED_STATES = {
    'approved',
    'declined',
    'obsolete',
    'review',
}
FRONTMATTER_REQUIRED_KEYS = {
    'creation_date',
    'state',
}
FRONTMATTER_OPTIONAL_KEYS = {
    'issues',  # to become required once all existing RFCs have it filled
    'last_review_date',
    'owners',  # to become required once all existing RFCs have it filled
    'summary',  # to become required once all existing RFCs have it filled
}
FRONTMATTER_KEYS_BECOMING_REQUIRED = {
    'issues',
    'owners',
    'summary',
}
FRONTMATTER_KEYS_BECOMING_REQUIRED_FROM_DATE = datetime.date(2023, 10, 12)
FRONTMATTER_ALL_KEYS = FRONTMATTER_REQUIRED_KEYS | FRONTMATTER_OPTIONAL_KEYS
GITHUB_OWNER_URL_REGEX = re.compile(
    # Single GitHub user (not recommended since single-people ownership is doomed to fail)
    r'^(https://github.com/[A-Za-z0-9][-A-Za-z0-9]*[A-Za-z0-9]'
    # Alternative URL format for individual people, as found on a team page
    r'|https://github.com/orgs/giantswarm/people/.+'
    # Most preferred: reference to a team
    r'|https://github.com/orgs/giantswarm/teams/.+)$')
ISSUE_URL_REGEX = re.compile(
    r'^(https://github.com/[A-Za-z0-9][-A-Za-z0-9]*[A-Za-z0-9]/[A-Za-z0-9][-A-Za-z0-9]*[A-Za-z0-9]/issues/[1-9][0-9]*$)'
)
OLD_RFC_NUMBER_IN_TITLE_REGEX = re.compile(r'RFC \d+\s*(-\s*)?')
TRAILING_WHITESPACE_REGEX = re.compile(r'[ \t\v]+$', flags=re.MULTILINE)


def check_rfc(rfc_dir):
    readme_file_path = os.path.join(rfc_dir, 'README.md')
    rfc = frontmatter.load(readme_file_path)
    problems = []

    if not rfc.metadata:
        # No YAML header, so the file is completely wrong. Stop checking here.
        problems.append(
            'README.md requires a YAML header as specified at '
            'https://github.com/giantswarm/rfc/tree/main/decision-process#decision-making-process')
        raise RfcFormatProblems(problems)

    unsupported_keys = set(rfc.metadata.keys()).difference(FRONTMATTER_ALL_KEYS)
    if unsupported_keys:
        problems.append(
            'Front matter YAML header has unsupported keys (please read '
            'https://github.com/giantswarm/rfc/tree/main/decision-process#rfc-file-structure): '
            f'{", ".join(sorted(unsupported_keys))}')

    missing_keys = FRONTMATTER_REQUIRED_KEYS.difference(rfc.metadata.keys())
    if missing_keys:
        problems.append(
            'Front matter YAML header is missing these keys (please read '
            'https://github.com/giantswarm/rfc/tree/main/decision-process#rfc-file-structure): '
            f'{", ".join(sorted(missing_keys))}')

    for date_key in ('creation_date', 'last_review_date'):
        if date_key not in rfc.metadata:
            continue

        # The YAML parser used in the `frontmatter` library will automatically use this type if the date is correctly
        # specified (format YYYY-MM-DD wanted)
        if not isinstance(rfc.metadata[date_key], datetime.date):
            problems.append(f'Front matter YAML header key "{date_key}" must be in format YYYY-MM-DD')
        elif not (2021 <= rfc.metadata[date_key].year <= 2100):
            problems.append(f'Front matter YAML header key "{date_key}" contains unexpected year')

    if (isinstance(rfc.metadata.get('creation_date'), datetime.date)
            and rfc.metadata['creation_date'] >= FRONTMATTER_KEYS_BECOMING_REQUIRED_FROM_DATE):
        missing_keys_required_in_new_rfcs = FRONTMATTER_KEYS_BECOMING_REQUIRED.difference(rfc.metadata.keys())
        if missing_keys_required_in_new_rfcs:
            problems.append(
                'Front matter YAML header is missing these keys (please read '
                'https://github.com/giantswarm/rfc/tree/main/decision-process#rfc-file-structure): '
                f'{", ".join(sorted(missing_keys_required_in_new_rfcs))}')

    if 'state' in rfc.metadata and rfc.metadata['state'] not in ALLOWED_STATES:
        problems.append(f'Front matter YAML header key "status" must be one of: {", ".join(sorted(ALLOWED_STATES))}')

    if 'summary' in rfc.metadata:
        rfc.metadata['summary'] = rfc.metadata['summary'].rstrip()
        if not rfc.metadata['summary']:
            problems.append(
                '`summary` is empty. Please provide 1-3 concise sentences, without paragraphs, describing '
                'the outcome/decision.')
        elif '\n' in rfc.metadata['summary']:
            problems.append(
                '`summary` should be short, but uses paragraphs. Please provide 1-3 concise sentences, without '
                'paragraphs, describing the outcome/decision.')

    if 'owners' in rfc.metadata:
        if not rfc.metadata['owners']:
            problems.append(
                'Front matter YAML header key "owners" must be a non-empty list (e.g. referencing one or more teams '
                'in the form `https://github.com/orgs/giantswarm/teams/sig-architecture`)')

        for owner in rfc.metadata['owners']:
            if not GITHUB_OWNER_URL_REGEX.match(owner):
                problems.append(
                    'Front matter YAML header key "owners" must be a non-empty list (e.g. referencing one or more teams '
                    'in the form `https://github.com/orgs/giantswarm/teams/sig-architecture`). Got invalid item: '
                    f'{owner!r}')

    # List of issues may be empty or null (not all decisions have a related issue)
    if 'issues' in rfc.metadata:
        if rfc.metadata['issues'] is not None and not isinstance(rfc.metadata['issues'], (tuple, list)):
            problems.append(
                'Front matter YAML header key "issues" must be a list of GitHub issue URLs or an empty list '
                '(NULL also allowed but not recommended)')

        for issue_url in (rfc.metadata['issues'] or ()):
            if not ISSUE_URL_REGEX.match(issue_url):
                problems.append(
                    'Front matter YAML header key "issues" must be a list of GitHub issue URLs or an empty list '
                    '(NULL also allowed but not recommended). Got invalid item: '
                    f'{issue_url!r}')

    with open(readme_file_path) as f:
        actual = f.read()

    actual_whitespace_trimmed = TRAILING_WHITESPACE_REGEX.sub('', actual)
    if actual_whitespace_trimmed != actual:
        diff_whitespace = ''.join(difflib.unified_diff(
            actual.splitlines(True),
            actual_whitespace_trimmed.splitlines(True),
            fromfile=readme_file_path,
            tofile=f'{readme_file_path}.no-trailing-whitespace',
            n=0,
        ))
        problems.append(
            'README.md must not have any trailing whitespace. Please configure your editor to always trim '
            'trailing whitespace in Markdown files.\n\n'
            'These are the affected lines:\n\n'
            f'{diff_whitespace}')

    if 'issues' in rfc.metadata and rfc.metadata['issues'] is None:
        # Prefer empty list when printing a patch diff below
        rfc.metadata['issues'] = []
    expected = frontmatter.dumps(
        rfc,
        # We want the front matter YAML header keys to be sorted alphabetically
        sort_keys=True,
        # Don't wrap long lines such as `summary: Sentence 1. Sentence 2. Sentence 3.` but keep them on one line.
        # It would be annoying to ask from authors to get the exact line wrapping length correct or update their PR
        # just because of some text wrapping differences.
        width=1000,
    ).rstrip('\n') + '\n'  # want exactly one newline at end of file

    # Show diff without trailing whitespace since that was already checked above
    expected = TRAILING_WHITESPACE_REGEX.sub('', expected)

    diff = ''.join(difflib.unified_diff(
        actual_whitespace_trimmed.splitlines(True),
        expected.splitlines(True),
        fromfile=readme_file_path,
        tofile=f'{readme_file_path}.patched',
    ))
    if diff:
        problems.append(f'Formatted output is different.\n\nPlease apply this patch:\n{diff}')

    # Find title (first H1 heading)
    markdown_content_lines = rfc.content.splitlines()
    for title_line_index, line in enumerate(markdown_content_lines):
        if line.startswith('# '):
            title = line[len('# '):].strip()

            # Some RFCs were titled after their GitHub PR number, but we didn't enforce such a numbering. Discard that part.
            title = OLD_RFC_NUMBER_IN_TITLE_REGEX.sub('', title)

            rfc.metadata['title'] = title
            rfc.metadata['markdown_content_without_title'] = (
                '\n'.join(markdown_content_lines[title_line_index + 1:]).lstrip().rstrip('\n') + '\n')

            break
        elif line.strip():
            problems.append(
                'Could not find title, or it was not the very first non-empty line after the YAML header. Please add '
                'a H1 heading (e.g. `# This is my RFC title`) directly after the YAML header. '
                f'Problematic line: {line!r}')
            break
    else:
        problems.append(
            'Could not find title. Please add a H1 heading (e.g. `# This is my RFC title`) after the YAML header.')

    if problems:
        raise RfcFormatProblems(problems)

    return rfc


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('rfc_repo_dir', help='Path to Git clone of https://github.com/giantswarm/rfc')
    parser.add_argument(
        '-o',
        '--output',
        help=(
            'If specified, all RFCs will be stored in this file, using a rather stable JSON format. '
            'Use `-` to output on stdout.'
        ))
    args = parser.parse_args()

    res = 0
    rfcs_json = []  # sorted in alphabetical order of directory names

    for entry_name in sorted(os.listdir(args.rfc_repo_dir)):
        # Each RFC is expected in a top-level directory, containing the main file `README.md`
        rfc_dir = os.path.join(args.rfc_repo_dir, entry_name)
        if not os.path.isdir(rfc_dir):
            continue
        readme_file_path = os.path.join(rfc_dir, 'README.md')
        if not os.path.exists(readme_file_path):
            continue

        try:
            rfc = check_rfc(rfc_dir)

            # Right now, this output only provides values relevant for rendering a table/summary of the RFCs
            # in the handbook.
            rfcs_json.append({
                'creation_date': rfc.metadata['creation_date'].isoformat(),
                'markdown_content_without_title': rfc.metadata['markdown_content_without_title'],
                'slug': entry_name,
                'state': rfc.metadata['state'],
                'summary': rfc.metadata.get('summary'),
                'title': rfc.metadata['title'],
            })
        except RfcFormatProblems as e:
            problems_str = '\n\n'.join(f'- {problem}' for problem in e.problems)
            print(f'Format problems in "{rfc_dir}":\n\n{problems_str}\n', file=sys.stderr)
            res = 1
        except Exception as e:
            if isinstance(e, yaml.YAMLError):
                e = (
                    f'Front matter is not a valid YAML header. The error was: {e}'
                    # Replace hint in the error message so the author knows in which file/line/column to look
                    .replace('in "<unicode string>", line', f'in "{readme_file_path}", line')
                )

            print(f'Error in "{rfc_dir}":\n\n{e}\n', file=sys.stderr)
            res = 1

    if res:
        print(
            'Please read the decision process https://github.com/giantswarm/rfc/tree/main/decision-process to learn '
            'about the expected file structure.',
            file=sys.stderr)

    if res == 0 and args.output is not None:
        out = open(args.output, 'w') if args.output != '-' else sys.stdout
        try:
            json.dump(rfcs_json, out, sort_keys=True, indent=4)
            out.write('\n')
        finally:
            if args.output != '-':
                out.close()

    return res


if __name__ == '__main__':
    sys.exit(main())
