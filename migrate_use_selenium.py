import os
import chromedriver_autoinstaller
import dotenv
import requests
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.common.exceptions import TimeoutException
from selenium.webdriver.support.wait import WebDriverWait

# initial setup
chromedriver_autoinstaller.install()
dotenv.load_dotenv()

GITLAB_URL = os.environ.get("GITLAB_URL")
GITLAB_TOKEN = os.environ.get("GITLAB_TOKEN")
GITEA_ADMIN_USER = os.environ.get("GITEA_ADMIN_USER")
GITEA_ADMIN_PASS = os.environ.get("GITEA_ADMIN_PASS")
GITEA_URL = os.environ.get("GITEA_URL")
GITLAB_API_BASE = f"{GITLAB_URL}/api/v4"
GITEA_API_BASE = f"{GITEA_URL}/api/v1"

GITEA_OWNER = "hiroshi"
WEBDRIVER_DURATION = 10


class check_multiple_elements(object):
    """複数のロケーターを用意してどちらかが見つかったらそれを返す"""

    # 複数のロケートを渡す
    def __init__(self, locator_list: list[tuple[str, str]]):
        self.locator_list = locator_list
        print(self.locator_list)

    # 複数を連続でチェックして、見つかった時点でelementを返す
    def __call__(self, driver):
        for locator in self.locator_list:
            locator_by = locator[0]
            locator_path = locator[1]
            # print(f"locate by:{locator_by} path:{locator_path}")

            element = driver.find_elements(locator_by, locator_path)
            if element:
                return element
        # 見つからない場合はFalseを返す
        return False


# メイン処理
gl_header = {"Private-Token": GITLAB_TOKEN}
gl_params = {"page": "1", "per_page": "100"}

## リポジトリをget
gl_project_res = requests.get(
    f"{GITLAB_API_BASE}/projects",
    headers=gl_header,
    params=gl_params,
)
gitlab_project_urls = [project.get("web_url") for project in gl_project_res.json()]

# 組織名をget
gl_project_namespace = (project.get("namespace") for project in gl_project_res.json())
gl_org_names = {
    namespace.get("full_path")
    for namespace in gl_project_namespace
    if namespace.get("kind") == "group"
}

# seleniumで操作していく
gitea_driver = webdriver.Chrome()
gitea_driver.get(f"{GITEA_URL}/user/login")
gitea_driver.find_element(By.ID, "user_name").send_keys(GITEA_ADMIN_USER)
gitea_driver.find_element(By.ID, "password").send_keys(GITEA_ADMIN_PASS)
gitea_driver.find_element(
    By.XPATH, "/html/body/div/div[2]/div[2]/div/div/form/div[4]/button"
).click()

# giteaの組織を作る
for org_name in gl_org_names:
    gitea_driver.get(f"{GITEA_URL}/org/create")

    org_name_input = WebDriverWait(gitea_driver, timeout=WEBDRIVER_DURATION).until(
        (lambda d: d.find_element(By.ID, "org_name"))
    )
    org_name_input.send_keys(org_name)

    org_visibility_check = gitea_driver.find_element(
        By.XPATH, "/html/body/div/div[2]/div/div/form/div/div[2]/div/div[3]/input"
    )
    gitea_driver.execute_script("arguments[0].click();", org_visibility_check)

    org_create_button = gitea_driver.find_element(
        By.XPATH, "/html/body/div/div[2]/div/div/form/div/div[4]/button"
    )

    gitea_driver.execute_script("arguments[0].click();", org_create_button)

    # 生成できたか条件チェック
    #
    org_sameorg_message = WebDriverWait(gitea_driver, timeout=WEBDRIVER_DURATION).until(
        check_multiple_elements(
            [
                (
                    By.XPATH,
                    "/html/body/div/div[2]/div/div/form/div/div[1]/p",
                ),  # すでに利用されているときのメッセージ
                (By.XPATH, "/html/body/div/div[2]/div[3]/div[1]/p"),  # 何用途か忘れてしまう
                (
                    By.XPATH,
                    "/html/body/div/div[2]/div[1]/div/div[3]/div/a",
                ),  # 作成成功後の組織ページにある右上ボタン
            ]
        )
    )
    if org_sameorg_message[0].text == "組織名が既に使用されています。":
        print(f"{org_name} is cant create errormsg -> :{org_sameorg_message[0].text}")
        continue


# 組織の一覧を見て、IDを取得する

gitea_driver.get(f"{GITEA_URL}/admin/orgs")
org_tbody = WebDriverWait(gitea_driver, timeout=WEBDRIVER_DURATION).until(
    (
        lambda d: d.find_element(
            By.XPATH, "/html/body/div/div[2]/div[2]/div[2]/table/tbody"
        )
    )
)

org_uids = [
    {
        "id": org_table_row.find_elements(By.TAG_NAME, "td")[0].text,
        "org_name": org_table_row.find_elements(By.TAG_NAME, "td")[1]
        .find_element(By.TAG_NAME, "a")
        .text,
    }
    for org_table_row in org_tbody.find_elements(By.TAG_NAME, "tr")
]

# giteaのmigrate
for project in gl_project_res.json():

    project_url = project.get("web_url")
    project_name = project.get("path")
    project_namespace = project.get("namespace")
    # gitlabのnamespaceがgroupならgiteaのorg idを探して摘要
    # 無ければ（面倒なので、現在のユーザー）

    if project_namespace.get("kind") == "group":
        gitea_org_id = next(
            i["id"]
            for i in org_uids
            if i["org_name"] == project_namespace.get("full_path")
        )
    else:
        gitea_org_id = 1

    print(f"Found {project_url} gitea uid:{gitea_org_id}: ")

    gitea_driver.get("f{GITEA_URL}/repo/migrate?service_type=4&org=&mirror=")
    WebDriverWait(gitea_driver, timeout=WEBDRIVER_DURATION).until(
        (lambda d: d.find_element(By.ID, "clone_addr"))
    ).send_keys(project_url)

    gitea_driver.find_element(By.ID, "auth_token").send_keys(GITLAB_TOKEN)

    labels_checkbox = gitea_driver.find_element(By.NAME, "labels")
    gitea_driver.execute_script("arguments[0].click();", labels_checkbox)
    issues_checkbox = gitea_driver.find_element(By.NAME, "issues")
    gitea_driver.execute_script("arguments[0].click();", issues_checkbox)
    pull_requests_checkbox = gitea_driver.find_element(By.NAME, "pull_requests")
    gitea_driver.execute_script("arguments[0].click();", pull_requests_checkbox)
    releases_checkbox = gitea_driver.find_element(By.NAME, "releases")
    gitea_driver.execute_script("arguments[0].click();", releases_checkbox)
    milestones_checkbox = gitea_driver.find_element(By.NAME, "milestones")
    gitea_driver.execute_script("arguments[0].click();", milestones_checkbox)

    # オーナーはuidを入れるだけ
    uid_input = gitea_driver.find_element(By.XPATH, '//*[@id="uid"]')
    gitea_driver.execute_script(f"arguments[0].value='{gitea_org_id}'", uid_input)

    # 実行
    go_clone_repo_button = WebDriverWait(gitea_driver, timeout=600).until(
        (
            lambda d: d.find_element(
                By.XPATH, "/html/body/div/div[2]/div/div/form/div/div[13]/button"
            )
        )
    )
    gitea_driver.execute_script("arguments[0].click();", go_clone_repo_button)

    # もしすでに作成済みのリポジトリなら無視して次へ
    result_elements = WebDriverWait(gitea_driver, timeout=600).until(
        check_multiple_elements(
            [
                (
                    By.XPATH,
                    "/html/body/div/div[2]/div/div/form/div/div[1]/p",
                ),  # マイグレーション中の画面
                (By.ID, "repo-clone-https"),  # マイグレーション成功
                (By.XPATH, '//*[@id="repo_migrating_failed"]'),  # マイグレーション失敗
            ]
        )
    )
    print(result_elements)
    match result_elements:
        case []:
            print("ng")
        case x if x[0].text == "リポジトリ名が既に使用されています。":
            print("ng")
        case x if x[0].get_attribute("id") == "repo_migrating_failed":
            print("ng")
        case _:
            print("ok")

gitea_driver.close()
