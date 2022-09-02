# gitlab-to-gitea-use-selenium

gitlab to gitea use python selenium

## Requirements

* python 3.10
* Google Chrome(use selenium)
* use requirements.txt `pip install -r requirements.txt`

## How to use

* rename `.env_sample` -> `.env`
* set config -> `.env`
* create virtual environment `python -m venv .venv`
* activate virtual environment
* `pip install -r requirements.txt`
* `python ./migurate_use_selenium.py`
* if migration error:
  * if issue id(iid) missing some parts, use `gitlab_create_issue_id.py`

## Reference

* Great Thanks!👏: <https://git.autonomic.zone/kawaiipunk/gitlab-to-gitea>
* <https://github.com/go-gitea/gitea/issues/14955#issuecomment-797285240>
