from apscheduler.util import undefined
from .job_classes import DeleteExpiredFilesJob

scheduler_jobs = []


def add_job(
    func,
    trigger=None,
    args=None,
    kwargs=None,
    id=None,
    name=None,
    misfire_grace_time=undefined,
    coalesce=undefined,
    max_instances=undefined,
    next_run_time=undefined,
    jobstore="default",
    executor="default",
    replace_existing=False,
    **trigger_args
):
    """
    將任務的設定打包成字典，並加入到 scheduler_jobs 列表中。
    """
    job_config = locals()
    job_config.pop("trigger_args", None)
    job_config.update(trigger_args)
    scheduler_jobs.append(job_config)


# 註冊「刪除過期檔案」任務，每小時執行一次
add_job(
    DeleteExpiredFilesJob().run,
    trigger="interval",
    hours=12,
    id="job_delete_expired_files",
)
