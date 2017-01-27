from heutagogy import app
import heutagogy.persistence as db
from heutagogy.auth import token_required

from flask_user import current_user
from flask import request
from flask_restful import Resource, Api

from http import HTTPStatus
import datetime
import aniso8601

api = Api(app)


@app.after_request
def after_request(response):
    response.headers.add('Access-Control-Allow-Origin', '*')
    if request.method == 'OPTIONS':
        response.headers['Access-Control-Allow-Methods'] = \
            'DELETE, GET, POST, PUT'
        headers = request.headers.get('Access-Control-Request-Headers')
        if headers:
            response.headers['Access-Control-Allow-Headers'] = headers
    return response


class Bookmarks(Resource):
    @token_required
    def get(self):
        current_user_id = current_user.id
        result = db.Bookmark.query.filter_by(user=current_user_id) \
                                  .paginate().items
        return list(map(lambda x: x.to_dict(), result))

    @token_required
    def post(self):
        r = request.get_json()

        if not r:
            return {'error': 'payload is mandatory'}, HTTPStatus.BAD_REQUEST

        if isinstance(r, dict):
            r = [r]

        bookmarks = []
        current_user_id = current_user.id
        now = datetime.datetime.utcnow().isoformat()

        for entity in r:
            if 'url' not in entity:
                return {'error': 'url field is mandatory'}, \
                    HTTPStatus.BAD_REQUEST

            if entity.get('read'):
                read = aniso8601.parse_datetime(entity.get('read'))
            else:
                read = None

            bookmarks.append(db.Bookmark(
                user=current_user_id,
                url=entity['url'],
                title=entity.get('title', None),
                timestamp=aniso8601.parse_datetime(
                    entity.get('timestamp', now)),
                read=read))

        for bookmark in bookmarks:
            db.db.session.add(bookmark)
        db.db.session.commit()

        res = list(map(lambda x: x.to_dict(), bookmarks))
        return res[0] if len(res) == 1 else res, HTTPStatus.CREATED


class Bookmark(Resource):
    @token_required
    def get(self, id):
        current_user_id = current_user.id
        bookmark = db.Bookmark.query \
                              .filter_by(id=id, user=current_user_id) \
                              .first()
        if bookmark is None:
            return {'error': 'Not found'}, HTTPStatus.NOT_FOUND
        return bookmark.to_dict()

    @token_required
    def post(self, id):
        update = request.get_json()
        if 'id' in update:
            return {'error': 'Updating id is not allowed'}, \
                HTTPStatus.BAD_REQUEST

        current_user_id = current_user.id
        bookmark = db.Bookmark.query \
                              .filter_by(id=id, user=current_user_id) \
                              .first()
        if bookmark is None:
            return {'error': 'Not found'}, HTTPStatus.NOT_FOUND

        if 'url' in update:
            bookmark.url = update['url']
        if 'title' in update:
            bookmark.title = update['title']
        if 'timestamp' in update:
            bookmark.timestamp = aniso8601.parse_datetime(update['timestamp'])
        if 'read' in update:
            if update['read']:
                bookmark.read = aniso8601.parse_datetime(update['read'])
            else:
                bookmark.read = None

        db.db.session.add(bookmark)
        db.db.session.commit()

        return bookmark.to_dict(), HTTPStatus.OK

    @token_required
    def delete(self, id):
        current_user_id = current_user.id
        bookmark = db.Bookmark.query \
                              .filter_by(id=id, user=current_user_id) \
                              .first()
        if bookmark is None:
            return {'error': 'Not found'}, HTTPStatus.NOT_FOUND

        db.db.session.delete(bookmark)
        db.db.session.commit()

        return {"id": bookmark.id}, HTTPStatus.OK


api.add_resource(Bookmarks, '/api/v1/bookmarks')
api.add_resource(Bookmark,  '/api/v1/bookmarks/<int:id>')
