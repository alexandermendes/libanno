# -*- coding: utf8 -*-
"""API base module.

Design notes:

- Content Negotiation: All responses are in the JSON-LD format and use the
  Web Annotation profile, more formats may be added in future.
"""

from flask import abort, request, jsonify, make_response
from jsonschema.exceptions import ValidationError
from sqlalchemy.exc import IntegrityError

try:
    from urllib import quote
    from urllib import urlencode
except ImportError:  # py3
    from urllib.parse import quote
    from urllib.parse import urlencode

from explicates.model.annotation import Annotation
from explicates.model.collection import Collection
from explicates.model.base import BaseDomainObject


class APIBase(object):

    def _get_domain_object(self, repo, id, **kwargs):
        """Return a domain object."""
        obj = repo.get_by(id=id, **kwargs)
        if not obj:
            abort(404)
        elif obj.deleted:
            abort(410)
        return obj

    def _get_iri(self, obj=None):
        """Return the IRI for a domain object."""
        full_path = request.path + obj.id + '/' if obj else request.path
        safe_path = quote(full_path.encode('utf8'))
        iri = request.host_url[:-1] + safe_path
        kwargs = request.args.copy()
        kwargs.pop('page', None)
        query_str = urlencode(kwargs)
        if query_str:
            iri += '?{}'.format(query_str)
        return iri

    def _create(self, model_class, repo, **kwargs):
        """Create a domain object and return a Respose."""
        data = request.get_json()
        slug = request.headers.get('Slug')

        try:
            obj = model_class(id=slug, data=data, **kwargs)
            repo.save(obj)
        except (ValidationError, IntegrityError, TypeError) as err:
            abort(400, err.message)

        response = self._create_response(obj)
        response.headers['Location'] = self._get_iri(obj)
        response.status_code = 201
        return response

    def _update(self, obj, repo):
        """Update a domain object and return a Respose."""
        data = request.get_json()
        try:
            obj.data = data
            repo.update(obj)
        except (ValidationError, IntegrityError, TypeError) as err:
            abort(400, err.message)

        response = self._create_response(obj)
        response.status_code = 200
        return response

    def _delete(self, obj, repo):
        """Delete a domain object and return a Respose."""
        try:
            repo.delete(obj.key)
        except (ValidationError, IntegrityError, TypeError) as err:
            abort(400, err.message)

        response = self._create_response(None)
        response.status_code = 204
        return response

    def _create_response(self, rv, status_code=200):
        """Return a Response.

        Currently, the server only supports the JSON-LD representation using
        the Web Annotation profile.

        See https://www.w3.org/TR/annotation-protocol/#annotation-retrieval
        """

        if not rv:
            out = {}
        elif isinstance(rv, BaseDomainObject):
            out = rv.dictize()
        elif isinstance(rv, dict):
            out = rv
        else:
            err_msg = '{} is not a valid return value'.format(type(rv))
            raise TypeError(err_msg)

        if out:
            if request.method == 'POST':
                out['id'] = self._get_iri(rv)
            else:
                out['id'] = self._get_iri()
            out['@context'] = "http://www.w3.org/ns/anno.jsonld"

        response = jsonify(out)

        profile = '"http://www.w3.org/ns/anno.jsonld"'
        response.mimetype = 'application/ld+json; profile={0}'.format(profile)

        # Add Etags for HEAD and GET requests
        if request.method in ['HEAD', 'GET']:
            response.add_etag()

        self._add_common_headers(response)
        self._add_link_headers(response, out)

        return response

    def _add_link_headers(self, response, out):
        """Add Link headers basic on the domain object."""
        types = out.get('type', [])
        if isinstance(types, basestring):
            types = [types]

        links = []
        if 'Annotation' in types:
            links.append({
                'url': 'http://www.w3.org/ns/ldp#Resource',
                'rel': 'type'
            })
        if 'AnnotationCollection' in types:
            links.append({
                'url': 'http://www.w3.org/ns/oa#AnnotationCollection',
                'rel': 'type'
            })
        if 'AnnotationPage' in types:
            links.append({
                'url': 'http://www.w3.org/ns/oa#AnnotationPage',
                'rel': 'type'
            })
        if 'BasicContainer' in types:
            links.append({
                'url': 'http://www.w3.org/ns/ldp#BasicContainer',
                'rel': 'type'
            })
            links.append({
                'url': 'http://www.w3.org/TR/annotation-protocol/',
                'rel': 'http://www.w3.org/ns/ldp#constrainedBy'
            })

        for link in links:
            link_str = '<{0}>; rel="{1}"'.format(link['url'], link['rel'])
            response.headers.add('Link', link_str)

    def _add_common_headers(self, response):
        """Add common headers for the API class."""
        common_headers = getattr(self, 'common_headers', {})
        response.headers.extend(common_headers)