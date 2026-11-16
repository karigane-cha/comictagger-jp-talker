# Repository guidance

## Scope and documentation

- This repository provides the Japanese Books Talker for ComicTagger. Maintain production code, tests, fixtures, and formal development specifications.
- Keep temporary research, diagnostics, and verification artifacts local by default, using `.research/` or another appropriate ignored directory.
- Do not automatically publish investigation or verification reports, add phase reports to `docs/`, or promote research notes to specifications.
- Give each public document a clear purpose and audience. When a formal specification changes, update the existing public specification as appropriate.
- In Japanese prose, put a half-width space between Japanese and alphanumeric characters. Separate consecutive katakana words when their combined length is at least eight characters.

## Git Branch and Workspace Policy

- Perform development work in the existing local Git repository.
- Create a new branch with `git switch -c <branch-name>` when isolation is required.
- Do not create a new repository inside the existing repository.
- Do not run `git clone` or `git init` inside the existing repository.
- Do not create nested Git repositories.
- Do not create additional Git worktrees unless explicitly requested.
- Check the current branch and `git status` before switching branches.
- Preserve all uncommitted changes and untracked files.

## Git staging and publication

- Do not run `git add` or `git commit` without explicit instruction. Pushing, merging branches or pull requests, deleting branches, and creating tags, releases, or pull requests also require explicit permission.
- Avoid `git add .`, `git add -A`, and `git add --all`. When authorized to stage, name each approved file individually.
- Check `git status --short` before staging and `git diff --cached --name-status` afterward; verify that the index contains no unrelated files.
- Do not stage research or verification reports for convenience, and never use `git add -f` on ignored files. If an ignored file needs publication, ask the user to approve an exception and adjust the ignore rules.
- Do not discard, modify, or move the user's uncommitted changes without authorization. Do not delete files or rewrite history without explicit authorization.
- Use English Conventional Commits for commit messages, for example `chore: update repository artifact policy`.

## Privacy and safety

- Do not assume local research is intended for publication. Avoid adding credentials, personal information, or environment-specific details.
- Check both GitHub and distribution packages for publication. Do not automatically stage files whose publication status is unclear; `.gitignore` does not untrack files already in Git.
- Preserve production and test safety boundaries. Keep P1/P2 publisher comparison read-only and isolated from normal execution and adoption decisions.
- P4/P5 remain on hold, and Publisher/Imprint auto-supplementation remains NO-GO until their separate prerequisites are met and a change is explicitly authorized.
- At the end of the work, report changed and untracked files.
