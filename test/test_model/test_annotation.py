# -*- coding: utf8 -*-

from flask import current_app
from mock import patch
from nose.tools import *
from sqlalchemy.exc import IntegrityError
from jsonschema.exceptions import ValidationError

from base import Test, db, with_context
from factories import CollectionFactory

from pywa.model.annotation import Annotation


class TestModelAnnotation(Test):

    def setUp(self):
        super(TestModelAnnotation, self).setUp()
        self.collection = CollectionFactory()
        self.annotation = Annotation(slug="foo",
                                     body="Simple body",
                                     target="http://example.com",
                                     collection=self.collection,
                                     collection_key=self.collection.key)

    @with_context
    def test_defaults(self):
        """Test Annotation is created with defaults."""
        db.session.add(self.annotation)
        db.session.commit()
        tmp = db.session.query(Annotation).get(1)
        assert_not_equal(tmp.slug, None)
        assert_not_equal(tmp.created, None)

    @with_context
    def test_get_id_suffix(self):
        """Test Annotation id suffix."""
        expected = u'{}/{}'.format(self.collection.slug, self.annotation.slug)
        id_suffix = self.annotation.get_id_suffix()
        assert_equal(id_suffix, expected)

    @with_context
    @patch('pywa.model.annotation.make_timestamp')
    def test_get_extra_info(self, mock_ts):
        """Test Annotation extra info."""
        fake_ts = 'foo'
        mock_ts.return_value = fake_ts
        extra_info = self.annotation.get_extra_info()
        assert_dict_equal(extra_info, {
            'type': 'Annotation',
            'generated': fake_ts,
            'generator': current_app.config.get('GENERATOR')
        })
