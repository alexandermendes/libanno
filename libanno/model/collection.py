# -*- coding: utf8 -*-

from flask import current_app
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.ext.hybrid import hybrid_property
from sqlalchemy.orm import relationship

from libanno.core import db
from libanno.model.base import BaseDomainObject
from libanno.model.annotation import Annotation


Base = declarative_base(cls=BaseDomainObject)


class Collection(db.Model, Base):
    """An annotation collection"""

    __tablename__ = 'collection'

    annotations = relationship(Annotation, backref='collection')

    def get_id_suffix(self):
        return u'{}/'.format(self.slug)

    @hybrid_property
    def total(self):
        return len(self.annotations)