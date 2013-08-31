# Original:
# Copyright (C) 2013 Google Inc.
#
# Modified by Matt Richardson
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Request Handler for /main endpoint."""

__author__ = 'alainv@google.com (Alain Vongsouvanh)'


import io
import jinja2
import logging
import os
import webapp2

from google.appengine.api import memcache
from google.appengine.api import urlfetch
from google.appengine.api import users

import httplib2
from apiclient import errors
from apiclient.http import MediaIoBaseUpload
from apiclient.http import BatchHttpRequest
from oauth2client.appengine import StorageByKeyName

from model import Credentials
from model import Note
import util


jinja_environment = jinja2.Environment(
    loader=jinja2.FileSystemLoader(os.path.dirname(__file__)))


class _BatchCallback(object):
  """Class used to track batch request responses."""

  def __init__(self):
    """Initialize a new _BatchCallbaclk object."""
    self.success = 0
    self.failure = 0

  def callback(self, request_id, response, exception):
    """Method called on each HTTP Response from a batch request.

    For more information, see
      https://developers.google.com/api-client-library/python/guide/batch
    """
    if exception is None:
      self.success += 1
    else:
      self.failure += 1
      logging.error(
          'Failed to insert item for user %s: %s', request_id, exception)


class MainHandler(webapp2.RequestHandler):
  """Request Handler for the landing page endpoint."""
  def _render_template(self, message=None):
    """Render the main page template."""

    # Query the DB for entries:
    notes_query = Note.all()
    notes_query.filter('public =', True)
    notes_query.order('-date')
    notes = notes_query.run()
    template_values = {'notes': notes}

    template = jinja_environment.get_template('templates/index.html')
    self.response.out.write(template.render(template_values))

  def get(self):
    """Render the main page."""
    self._render_template()

class UserHandler(webapp2.RequestHandler):
  """Request Handler for the user backend endpoint."""

  def _render_template(self, message=None):
    """Render the user page template."""

    notes_query = Note.all()
    notes_query.order('-date')
    notes_query.filter('userId =', self.userid)
    notes = notes_query.run()
    template_values = {'notes': notes}

    displayName = StorageByKeyName(Credentials, self.userid, 'displayName').get()
    template_values['displayName'] = displayName

    template_values['approved'] = StorageByKeyName(Credentials, self.userid, 'approved').get()

    template = jinja_environment.get_template('templates/contributor.html')
    self.response.out.write(template.render(template_values))

  @util.auth_required
  def get(self):
    """Render the main page."""
    # Get the flash message and delete it.
    message = memcache.get(key=self.userid)
    memcache.delete(key=self.userid)
    self._render_template()

  @util.auth_required
  def post(self):
    """Execute the request and render the template."""
    operation = self.request.get('operation')
    # Dict of operations to easily map keys to methods.
    operations = {
        'changeDisplayName': self._change_display_name,
    }
    if operation in operations:
      message = operations[operation]()
    else:
      message = "I don't know how to " + operation
    # Store the flash message for 5 seconds.
    memcache.set(key=self.userid, value=message, time=5)
    self.redirect('/contributor')

  def _change_display_name(self):
    """Change display name."""
    displayName = self.request.get('displayName')
    StorageByKeyName(Credentials, self.userid, 'displayName').put(displayName)
    return 'Display name changed.'

MAIN_ROUTES = [
    ('/', MainHandler),
    ('/contributor', UserHandler)
]
