# ref: https://github.com/go-gitea/gitea/issues/14955#issuecomment-797285240

import os
import requests
import dotenv

dotenv.load_dotenv()

GITLAB_TOKEN = os.environ.get("GITLAB_TOKEN")
GITLAB_URL = os.environ.get("GITLAB_URL")

GITLAB_API_BASE = f"{GITLAB_URL}/api/v4"

# 必要な情報：内容は例
# GitlabのプロジェクトIDはSettings>Generalで確認可能
project_id = "20"
# issueのid -> iid
project_issue_iid = "15"

# メイン処理：安全を考えてひとつづつ実行
gl_header = {"Private-Token": GITLAB_TOKEN, "content-type": "application/json"}
gl_params = {"title": "Empty issue for Gitea migration", "iid": project_issue_iid}

gl_create_issue = requests.post(
    f"{GITLAB_API_BASE}/projects/{project_id}/issues",
    headers=gl_header,
    params=gl_params,
)

# 雑な結果表示
print(gl_create_issue.status_code)
print(gl_create_issue.text)
