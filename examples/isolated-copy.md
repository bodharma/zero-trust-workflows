# Independent private-copy runbook

Use this runbook for organization-specific changes that must stay private.
Public GitHub forks remain public and share a repository network; there is no
private-fork operation for this public repository. A local clone alone does
not create a private GitHub repository. See
[GitHub's fork documentation](https://docs.github.com/en/pull-requests/reference/forks).

Run these commands on a trusted machine inside your private boundary with
Git, GitHub CLI, and uv installed. Authenticate GitHub CLI and Git for the
intended private organization. Replace the uppercase placeholders before
running a command. Keep private modifications and review evidence out of the
public repository and its issues.

1. **Create an empty private repository, not a fork.** Choose the owner and
   name, then verify its visibility and network membership before importing.

   ```sh
   private_repository="YOUR_ORG/PRIVATE_WORKFLOWS"
   gh repo create "$private_repository" --private
   gh repo view "$private_repository" --json nameWithOwner,visibility,isFork
   ```

   Proceed only when `visibility` is `PRIVATE` and `isFork` is `false`.

2. **Import a reviewed release commit.** Review the release and resolve its
   exact 40-hex SHA. No supported release exists yet; importing the current
   experimental commit requires accepting its experimental status. Preserve
   `LICENSE` and attribution when copying. This imports Git history into the
   independent repository created above, without joining the fork network.

   ```sh
   release_sha="REPLACE_WITH_REVIEWED_40_HEX_SHA"
   git init isolated-workflows
   cd isolated-workflows
   git remote add origin "git@github.com:${private_repository}.git"
   git remote add upstream https://github.com/bodharma/zero-trust-workflows.git
   git remote set-url --push upstream disabled://public-upstream
   git fetch --no-tags upstream "$release_sha"
   git switch -c main FETCH_HEAD
   git rev-parse HEAD
   ```

   Confirm `HEAD` equals the reviewed release SHA. GitHub's template operation
   is an alternative only if the public repository is configured as a template;
   it must create an independent private repository, and its imported content
   still needs review against the chosen release.

3. **Remove writable public-upstream push access.** Keep `origin` pointing
   only to the independent private repository. The upstream remote was given
   a disabled push URL before import; enforce it again and inspect every remote.

   ```sh
   git remote set-url --push upstream disabled://public-upstream
   git remote -v
   gh repo view "$private_repository" --json nameWithOwner,visibility,isFork
   ```

   Remove any other public push remote before making private changes. Use
   credentials without public-upstream write permission and remove any
   public-upstream write grants or writable deploy keys. Keep an upstream
   remote only for fetching reviewed public commits. A disabled remote push
   URL is a local guard, not a substitute for removing write authorization.

4. **Check the imported code inside the private boundary.** Run the fixed
   dependency and verification commands before pushing the private copy.

   ```sh
   uv sync --locked --dev && make check
   git push -u origin main
   ```

   Preserve the command output as private review evidence. The private copy's
   self-CI calls its local reusable workflow. For other private consumers, pin
   the independent repository's workflow to its reviewed full SHA and configure
   GitHub Actions access within the organization; calling the public coordinate
   continues to use the public implementation.

5. **Import updates only through a reviewed diff.** Record the previously
   imported public SHA, proposed public SHA, and current private rollback SHA.
   Fetch the new full SHA, review its complete diff, then merge on a private
   review branch and resolve any conflicts inside the private boundary.

   ```sh
   old_sha="REPLACE_WITH_PREVIOUS_PUBLIC_40_HEX_SHA"
   new_sha="REPLACE_WITH_REVIEWED_PUBLIC_40_HEX_SHA"
   git rev-parse HEAD
   git fetch --no-tags upstream "$new_sha"
   git diff "$old_sha" "$new_sha"
   git switch -c reviewed-upstream-update
   git merge --no-commit --no-ff "$new_sha"
   uv sync --locked --dev && make check
   ```

   Store old SHA, new SHA, test command/output, and the pre-merge private
   rollback SHA in the private change record. Commit and submit the update to
   the private repository only after review and passing checks. Roll back a
   committed merge with a reviewed revert in the private repository, or restore
   the prior full-SHA caller pin. Preserve local changes; never export the
   private diff, history, or review record to the public upstream.
