from datetime import date, datetime, time
from typing import Iterator, Optional

from app.internal.security.schema import CurrentUser
from app.database.models import User, Task, WeeklyTask
from sqlalchemy.orm.session import Session


def check_inputs(days: str, task_time: time, title: str) -> bool:
    """Checks inputs, used by the weekly_task_from_input function"""
    return days and task_time and title


def weekly_task_from_input(
    user: User,
    title: Optional[str],
    days: str,
    content: Optional[str],
    task_time: Optional[time],
    is_important: bool,
    weekly_task_id: int = 0,
) -> WeeklyTask:
    """This function is being used to make a Weekly Task model
        from the inputs.

    Args:
        user (User): The user who wants to make or edit a Weekly Task.
        title (str): Title of the Weekly Task.
        days (str): Return days of the Weekly Task.
        content (str): Content of the Weekly Task.
        task_time (time): Return time of the Weekly Task.
        is_important (bool): If the task is important.
        weekly_task_id (int): The id of the weekly task, zero if not mentioned.

    Returns:
        WeeklyTask: the model WeeklyTask which the function managed to make.
    """
    if isinstance(user, CurrentUser):
        user_id = user.user_id
    else:
        user_id = user.id
    weekly_task = WeeklyTask(
        title=title,
        content=content,
        is_important=is_important,
        user_id=user_id,
    )

    if weekly_task_id != 0:
        weekly_task.id = weekly_task_id

    inputs_ok = check_inputs(days, task_time, title)
    if not inputs_ok:
        return weekly_task
    weekly_task.set_days(days)
    weekly_task.task_time = task_time.strftime("%H:%M")
    return weekly_task


def create_weekly_task(
    weekly_task: WeeklyTask,
    session: Session,
) -> bool:
    """This function is being used to add a Weekly Task to the user.

    Args:
        user (User): The user who wants to add the Weekly Task.
        session (Session): The session to redirect to the database.
        weekly_task (WeeklyTask): The Weekly Task that the user will add.

    Returns:
        bool: Shows if the weekly_task has been added to the db.
    """
    inputs_ok = check_inputs(
        weekly_task.days,
        weekly_task.task_time,
        weekly_task.title,
    )
    if not inputs_ok:
        return False
    session.add(weekly_task)
    session.commit()
    return True


def change_weekly_task(
    user: User,
    weekly_task: WeeklyTask,
    session: Session,
) -> bool:
    """This function is being used to edit a Weekly Task the user have.

    Args:
        user (User): The user who wants to edit the Weekly Task.
        session (Session): The session to redirect to the database.
        weekly_task (WeeklyTask): The Weekly Task that the of the user,
            with the edited values.

    Returns:
        bool: Shows if the weekly_task has been edited in the db.
    """
    inputs_ok = check_inputs(
        weekly_task.days,
        weekly_task.task_time,
        weekly_task.title,
    )
    if not inputs_ok:
        return False
    w_task_query = session.query(WeeklyTask)
    old_weekly_task = w_task_query.filter_by(id=weekly_task.id).first()

    if weekly_task.user_id != user.id:
        return False

    old_weekly_task.title = weekly_task.title
    old_weekly_task.days = weekly_task.days
    old_weekly_task.content = weekly_task.content
    old_weekly_task.is_important = weekly_task.is_important
    old_weekly_task.task_time = weekly_task.task_time
    session.commit()
    return True


def create_task(task: Task, user: User, session: Session) -> bool:
    """Make a task, used by the generate_tasks function"""
    user_tasks_query = session.query(Task).filter_by(owner_id=user.id)
    task_by_time = user_tasks_query.filter_by(time=task.time)
    task_by_date_time = task_by_time.filter_by(date=task.date)
    task_by_title_and_time = task_by_date_time.filter_by(title=task.title)
    task_exist = task_by_title_and_time.first()
    if task_exist:
        return False
    session.add(task)
    session.commit()
    return True


def get_datetime(day: str, task_time: str) -> datetime:
    """Getting the datetime of days in the current week,
    used by the generate_tasks function"""
    current_date = date.today()
    current_week_num = current_date.strftime("%W")
    current_year = current_date.strftime("%Y")
    date_string = f"{day} {task_time} {current_week_num} {current_year}"
    return datetime.strptime(date_string, "%a %H:%M %W %Y")


def generate_tasks(user: User, session: Session) -> Iterator[bool]:
    """Generates tasks for the week
    based on all the weekly tasks the user have"""
    for weekly_task in user.weekly_tasks:
        task_time = weekly_task.task_time
        days = weekly_task.get_days()
        days_list = days.split(", ")
        for day in days_list:
            date_time = get_datetime(day, task_time)
            task = Task(
                title=weekly_task.title,
                description=weekly_task.content,
                is_done=False,
                is_important=weekly_task.is_important,
                date=date_time.date(),
                time=date_time.time(),
                owner_id=user.id,
            )
            yield create_task(task, user, session)


def remove_weekly_task(weekly_task_id: int, session: Session) -> bool:
    """Removes a weekly task from the db based on the weekly task id"""
    weekly_task_query = session.query(WeeklyTask)
    weekly_task = weekly_task_query.filter_by(id=weekly_task_id).first()
    if not weekly_task:
        return False
    session.query(WeeklyTask).filter_by(id=weekly_task_id).delete()
    session.commit()
    return True