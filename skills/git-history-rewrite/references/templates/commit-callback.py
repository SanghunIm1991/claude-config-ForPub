# git filter-repo の --commit-callback に渡す処理のひな形。
# コメント行（#で始まる行）は実行時に grep -v '^#' で取り除いて渡すため、コード部分には日本語を書かない。
# 1) 旧 author（例: ClaudeCode）のコミットに Co-Authored-By 行がなければ追加する
# 2) 旧 author・旧 committer のメールアドレスを、新しい名義（GitHubのnoreplyアドレス推奨）に置き換える
NEW_NAME = b"<GitHubのユーザー名>"
NEW_EMAIL = b"<ID>+<ユーザー名>@users.noreply.github.com"
OLD_EMAILS = {b"noreply@anthropic.com", b"<旧メールアドレス>"}
if commit.author_email == b"noreply@anthropic.com" and b"Co-Authored-By:" not in commit.message:
    commit.message = commit.message.rstrip(b"\n") + b"\n\nCo-Authored-By: Claude <noreply@anthropic.com>\n"
if commit.author_email in OLD_EMAILS:
    commit.author_name, commit.author_email = NEW_NAME, NEW_EMAIL
if commit.committer_email in OLD_EMAILS:
    commit.committer_name, commit.committer_email = NEW_NAME, NEW_EMAIL
