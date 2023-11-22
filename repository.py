from sqlalchemy import and_
from sqlalchemy.sql import func

from model import Poll, SessionLocal, User


class PollRepository:
    def __init__(self, session=SessionLocal, model=Poll):
        self.session = session()
        self.model = model

    def get(self, chat_id: str | None = None, start_time: str | None = None, end_time: str | None = None, poll_id: str | None = None, dow: str | None = None):
        if chat_id:
            polls = self.session.query(self.model).filter(self.model.chat_id==chat_id).all()
        elif start_time and dow:
            polls = self.session.query(self.model).filter(and_(self.model.start_time==start_time, self.model.dows.like(f"{dow}"))).all()
        elif end_time and dow:
            polls = self.session.query(self.model).filter(and_(self.model.end_time==end_time, self.model.dows.like(f"{dow}"))).all()
        elif poll_id:
            polls = self.session.query(self.model).filter(self.model.poll_id==poll_id).all()
        else:
            polls = self.session.query(self.model).all()
        return (poll for poll in polls)

    def add(self, poll_data: Poll):
        self.session.add(poll_data)
        self.session.commit()

    def update(self, poll: Poll):
        self.session.add(poll)
        self.session.commit()

    def delete(self, poll_id: int):
        poll = self.session.query(self.model).filter(self.model.id==poll_id).first()
        self.session.delete(poll)
        self.session.commit()

class UserRepository:
    def __init__(self, session=SessionLocal, model=User):
        self.session = session()
        self.model = model

    def get(self, chat_id: str, user_id: str):
        polls = self.session.query(self.model.name, self.model.poll_question, func.count(self.model.user_options)).group_by(self.model.user_id, self.model.poll_question).filter(and_(self.model.chat_id==chat_id, self.model.user_id==user_id)).all()
        return (poll for poll in polls)


    def add(self, user_data: User):
        if len(self.session.query(self.model).filter(and_(self.model.user_id==user_data.user_id, self.model.poll_id==user_data.poll_id)).all()) > 0:
            user = self.session.query(self.model).filter(and_(self.model.user_id==user_data.user_id, self.model.poll_id==user_data.poll_id)).first()
            if user_data.user_options == "":
                user.user_options = None
            else:
                user.user_options = user_data.user_options
        else:
            self.session.add(user_data)
        self.session.commit()

poll_repo, user_repo = PollRepository(), UserRepository()