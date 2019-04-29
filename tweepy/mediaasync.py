# Tweepy Async Media Upload
# written by David Standish (https://github.com/machine-uprising)
# February 2019
#
# Tweepy
# Copyright 2010 Joshua Roesslein
# See LICENSE for details.

from __future__ import print_function
from tweepy.error import TweepError, RateLimitError, is_rate_limit_error_message

import os
import time

import requests
import mimetypes


def media_async_api(**config):
    """ Async Media Uploader base on the twitterdev GitHub repository
    large-video-upload-python
    https://github.com/twitterdev/large-video-upload-python
    """
    class MediaUpload(object):

        api = config['api']
        path = config['path']
        payload_type = config.get('payload_type', None)
        payload_list = config.get('payload_list', False)
        allowed_param = config.get('allowed_param', [])
        method = config.get('method', 'GET')
        require_auth = config.get('require_auth', False)
        search_api = config.get('search_api', False)
        upload_api = config.get('upload_api', False)
        use_cache = config.get('use_cache', True)
        session = requests.Session()

        def __init__(self, args, kwargs):
            """ Prepared file properties for file being uploaded """

            api = self.api
            # If authentication is required and no credentials
            # are provided, throw an error.
            if self.require_auth and not api.auth:
                raise TweepError('Authentication required!')
            self.post_data = kwargs.pop('post_data', None)
            self.post_json = kwargs.pop('post_json',False)

            self.media_filename = kwargs.pop('media_filename',None)
            if self.media_filename is None:
                raise TweepError('No Media File Provided for Uploading')

            if not os.path.exists(self.media_filename):
                raise TweepError('Invalid Media File - File Not Found')

            self.total_bytes = os.path.getsize(self.media_filename)
            self.media_category = kwargs.pop('media_category',None)
            self.additional_owners = kwargs.pop('additional_owners',None)
            self.shared_media = kwargs.pop('shared',False)
            self.media_type = None
            self.file_media_type()

            self.media_id = None
            self.media_info = None
            self.processing_info = None

            self.parser = kwargs.pop('parser',api.parser)
            self.session.headers = kwargs.pop('headers', {})

            self.host = api.upload_host
            self.api_root = api.upload_root
            self.session.headers['Host'] = self.host

            # Twitter API Documentation states that 'multipart-form' Content-Type
            # is required for async uploading on the INIT,APPEND,FINALIZE stages
            # but it produced errors in testing.
            # Excluding this option allowed for async upload to work correctly
            #self.session.headers['Content-Type'] = 'multipart/form-data'


        def file_media_type(self):
            """ Identify the mime type of the file. If mime type
            cannot be identified then TweepError is raised """
            valid_media_types = {
                'image':['gif','jpg','jpeg','png'],
                'video':['mp4']
            }

            try:
                media_type = mimetypes.guess_type(self.media_filename)
            except Exception as e:
                raise TweepError('Unable to capture media type for media file')

            if isinstance(media_type,tuple):
                media_type = media_type[0]
            else:
                raise TweepError('Media type did not return a tuple item')

            if "/" in media_type:
                media_type_split = media_type.split('/')
            else:
                raise TweepError('Cannot split media type in categories')

            if media_type_split[0] not in valid_media_types.keys():
                raise TweepError(
                    'Media type is invalid. Must be image or video')

            if media_type_split[1] not in valid_media_types[media_type_split[0]]:
                raise TweepError(
                    'Extension Type is invalid for %s media type'%media_type_split[0])

            self.media_type = media_type


        def upload_execute(self, upload_stage, **kwargs):
            url = self.api_root + self.path
            full_url = 'https://' + self.host + url

            auth = None
            if self.api.auth:
                auth = self.api.auth.apply_auth()

            params = {}
            post_data = {}
            file_data = {}

            if upload_stage in ['init','finalize']:
                post_data = kwargs.pop('post_data',None)
                self.method = 'POST'
            elif upload_stage == 'append':
                post_data = kwargs.pop('post_data',None)
                file_data = kwargs.pop('file_data',None)
                self.method = 'POST'
            elif upload_stage == 'status':
                self.method = 'GET'
                params = kwargs.pop('params')
            else:
                raise TweepError('Invalid upload stage: %s' % upload_stage)

            try:
                resp = self.session.request(self.method,
                                            full_url,
                                            params=params,
                                            data=post_data,
                                            files=file_data,
                                            timeout=self.api.timeout,
                                            auth=auth,
                                            proxies=self.api.proxy)
            except Exception as e:
                raise TweepError('Failed to send request: %s' % e)

            if resp.status_code and not 200 <= resp.status_code < 300:
                try:
                    error_msg, api_error_code = \
                        self.parser.parse_error(resp.text)
                except Exception as e:
                    error_msg = 'Twitter error response: status code = %s' % resp.status_code
                    api_error_code = None

                if is_rate_limit_error_message(error_msg):
                    raise RateLimitError(error_msg)
                else:
                    error_msg = resp.text
                    raise TweepError(error_msg, resp, api_code=api_error_code)

            if upload_stage == 'append':
                # The append async stage only returns a 2XX HTTP response so
                # the append upload stage just returns a True value. Errors
                # would be caught above in the status code check
                return True
            else:
                result = self.parser.parse(self, resp.text)

            return result


        def upload_init(self):
            """ Initializes Upload
            :reference: https://developer.twitter.com/en/docs/media/upload-media/api-reference/post-media-upload-init
            """

            upload_stage = 'init'
            post_data = {
              'command': 'INIT',
              'media_type': self.media_type,
              'total_bytes': self.total_bytes
            }

            if self.media_category is not None:
                post_data.update({'media_category':self.media_category})

            if self.additional_owners is not None:
                post_data.update({'additional_owners':self.additional_owners})

            post_data.update({'shared':self.shared_media})

            kwargs = dict()
            kwargs.update({'post_data':post_data})

            response = self.upload_execute(upload_stage, **kwargs)

            try:
                self.media_id = response._json["media_id"]
                self.media_info = response._json
            except Exception as e:
                raise TweepError('Upload Error: Did not receive media_id')

            return self


        def upload_append(self):
            """ Uploads and appends media in chunks
            :reference: https://developer.twitter.com/en/docs/media/upload-media/api-reference/post-media-upload-append
            """
            segment_id = 0
            bytes_sent = 0
            mb_per_chunk = 4

            if os.path.exists(self.media_filename):
                file = open(self.media_filename, 'rb')
            else:
                raise TweepError('File Not Found: Cannot find media file')

            while bytes_sent < self.total_bytes:
                chunk = file.read(mb_per_chunk*1024*1024)

                upload_stage = 'append'

                post_data = {
                'command': 'APPEND',
                'media_id': self.media_id,
                'segment_index': segment_id
                }

                file_data = {
                'media':chunk
                }

                kwargs = dict()
                kwargs.update({'post_data':post_data})
                kwargs.update({'file_data':file_data})

                response = self.upload_execute(upload_stage, **kwargs)
                try:
                    response == True
                except Exception as e:
                    raise TweepError('Upload Error: Did not receive media_id')

                segment_id = segment_id + 1
                bytes_sent = file.tell()

            return self


        def upload_finalize(self):
            """ Finalizes uploads and starts video processing
            :reference:https://developer.twitter.com/en/docs/media/upload-media/api-reference/post-media-upload-finalize
            """
            upload_stage = 'finalize'

            post_data = {
              'command': 'FINALIZE',
              'media_id': self.media_id
            }
            kwargs = dict()
            kwargs.update({'post_data':post_data})

            response = self.upload_execute(upload_stage, **kwargs)
            try:
                self.processing_info = response["processing_info"]
            except Exception as e:
                self.processing_info = None

            try:
                del self.session.headers['Content-Type']
            except:
                pass

            self.check_status()

            return self.media_info


        def check_status(self):
            """ Checks video processing status
            :reference: https://developer.twitter.com/en/docs/media/upload-media/api-reference/get-media-upload-status
            """
            if self.processing_info is None:
              return

            state = self.processing_info['state']

            if state == u'succeeded':
              return

            if state == u'failed':
              raise TweepError('Upload Status Check Failed')

            check_after_secs = self.processing_info['check_after_secs']

            time.sleep(check_after_secs)

            upload_stage = 'status'
            params = {
              'command': 'STATUS',
              'media_id': self.media_id
            }

            kwargs = dict()
            kwargs.update({'params':params})
            response = self.upload_execute(upload_stage, **kwargs)

            try:
                self.processing_info = response["processing_info"]
            except Exception as e:
                self.processing_info = None

            self.check_status()


        def upload(self):
            """ Runs the async media upload process from start to finish.
            Upload is a three stage process so chaining has been applied to
            the function calls
            """
            media_info = None
            media_info = self.upload_init().upload_append().upload_finalize()
            return media_info


    def _call(*args, **kwargs):
        method = MediaUpload(args, kwargs)
        if kwargs.get('create'):
            return method
        else:
            return method.upload()

    return _call
