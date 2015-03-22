
"""Unit tests"""

import unittest

from git_slack import slack, response


def populate_flags(push):
    """Populate created/deleted flags in pull object"""
    push['created'] = all(c == '0' for c in push['before'])
    push['deleted'] = all(c == '0' for c in push['after'])


class TestPushResponse(unittest.TestCase):
    def setUp(self):
        self.minimal_push = {
            'before': '124bf239bd5068f647597e5d435557da68edb047',
            'after': 'a697150fd92f21ca186ac0f43cdef6000e6c3d2f',
            'ref': 'refs/heads/master',
            'commits': [
                {'id': 'a697150fd92f21ca186ac0f43cdef6000e6c3d2f',
                 'message': 'Test commit',
                 'author': {
                     'name': 'Test Person'
                 }
             }],
            'repository': {
                'full_name': 'testing'
            }
        }
        populate_flags(self.minimal_push)

    def test_minimal_push_has_slack_defaults(self):
        message = response.message_from_push(self.minimal_push).document()
        self.assertNotIn('username', message)
        self.assertNotIn('channel', message)

    def test_minimal_push_has_no_text(self):
        message = response.message_from_push(self.minimal_push).document()
        self.assertNotIn('test', message)

    def test_minimal_push_has_one_attachment(self):
        message = response.message_from_push(self.minimal_push).document()
        self.assertIn('attachments', message)
        self.assertIsInstance(message['attachments'], list)
        self.assertEqual(len(message['attachments']), 1)

    def test_minimal_push_attachment_has_fallback(self):        
        message = response.message_from_push(self.minimal_push).document()
        attachment = message['attachments'][0]
        self.assertIn('fallback', attachment)
        self.assertEqual(attachment['fallback'],
                         '[testing:master] one new commit')

    def test_minimal_push_attachment_has_pretext(self):
        message = response.message_from_push(self.minimal_push).document()
        attachment = message['attachments'][0]
        self.assertIn('pretext', attachment)
        self.assertEqual(attachment['pretext'],
                         '[testing:master] one new commit:')

    def test_minimal_push_attachment_has_color(self):
        message = response.message_from_push(self.minimal_push).document()
        attachment = message['attachments'][0]
        self.assertIn('color', attachment)

    def test_minimal_push_attachment_has_text(self):
        message = response.message_from_push(self.minimal_push).document()
        attachment = message['attachments'][0]
        self.assertIn('text', attachment)
        self.assertEqual(attachment['text'],
                         slack.Markup('a697150: Test commit - Test Person'))

    def test_tag_push_creates_no_message(self):
        push = self.minimal_push
        push['ref'] = 'refs/tags/v1.0'
        message = response.message_from_push(push)
        self.assertIsNone(message)

    def test_delete_push_creates_no_message(self):
        push = self.minimal_push
        push['after'] = 40*'0'
        push['deleted'] = True
        push['commits'] = []
        message = response.message_from_push(push)
        self.assertIsNone(message)

    def test_reset_push_creates_no_message(self):
        push = self.minimal_push
        push['after'], push['before'] = push['before'], push['after']
        push['commits'] = []
        message = response.message_from_push(push)
        self.assertIsNone(message)

    def test_minimal_push_with_custom_username(self):
        message = response.message_from_push(
            self.minimal_push, slack_username='testuser').document()
        self.assertIn('username', message)
        self.assertEqual(message['username'], 'testuser')

    def test_minimal_push_with_custom_channel(self):
        message = response.message_from_push(
            self.minimal_push, slack_channel='#mychannel').document()
        self.assertIn('channel', message)
        self.assertEqual(message['channel'], '#mychannel')

    def test_minimal_push_with_linked_repo(self):
        push = self.minimal_push
        push['repository']['url'] = 'http://example.com/testing'
        message = response.message_from_push(push).document()
        attachment = message['attachments'][0]

        self.assertEqual(attachment['fallback'],
                         '[testing:master] one new commit')

        pretext = slack.Markup(
            '[<http://example.com/testing|testing>:master]'
            ' one new commit:')
        self.assertEqual(attachment['pretext'], pretext)

    def test_minimal_push_with_linked_branch(self):
        push = self.minimal_push
        push['url'] = 'http://example.com/testing?t=tree&b=master'
        message = response.message_from_push(push).document()
        attachment = message['attachments'][0]

        self.assertEqual(attachment['fallback'],
                         '[testing:master] one new commit')

        pretext = slack.Markup(
            '[testing:'
            '<http://example.com/testing?t=tree&amp;b=master|master>'
            '] one new commit:')
        self.assertEqual(attachment['pretext'], pretext)

    def test_minimal_push_with_linked_commit(self):
        push = self.minimal_push
        push['commits'][0]['url'] = (
            'http://example.com/testing?t=commit&c=a697150')
        message = response.message_from_push(push).document()
        attachment = message['attachments'][0]

        text = slack.Markup(
            '<http://example.com/testing?t=commit&amp;c=a697150|a697150>:'
            ' Test commit - Test Person')
        self.assertEqual(attachment['text'], text)


class TestRules(unittest.TestCase):
    def test_push_exclude_rule_applying_to_repository(self):
        push = {
            'ref': 'refs/heads/master',
            'repository': {'full_name': 'testing'}
        }
        rules = [{
            'filter': 'exclude',
            'repository': 'test.*'
        }]

        result = list(response.apply_rules(push, rules))
        self.assertEqual(result, [])

    def test_push_exclude_rule_not_applying_to_repository(self):
        push = {
            'ref': 'refs/heads/master',
            'repository': {'full_name': 'testing'}
        }
        rules = [{
            'filter': 'exclude',
            'repository': 'user/.*'
        }]

        result = list(response.apply_rules(push, rules))
        self.assertEqual(result, [(push, None, None)])

    def test_push_exclude_rule_applying_to_branch(self):
        push = {
            'ref': 'refs/heads/master',
            'repository': {'full_name': 'testing'}
        }
        rules = [{
            'filter': 'exclude',
            'branch': 'master'
        }]

        result = list(response.apply_rules(push, rules))
        self.assertEqual(result, [])

    def test_push_exclude_rule_not_applying_to_branch(self):
        push = {
            'ref': 'refs/heads/master',
            'repository': {'full_name': 'testing'}
        }
        rules = [{
            'filter': 'exclude',
            'branch': 'release-.*'
        }]

        result = list(response.apply_rules(push, rules))
        self.assertEqual(result, [(push, None, None)])

    def test_push_include_rule_applying_to_repository(self):
        push = {
            'ref': 'refs/heads/master',
            'repository': {'full_name': 'testing'}
        }
        rules = [{
            'filter': 'include',
            'repository': 'test.*'
        }]

        result = list(response.apply_rules(push, rules))
        self.assertEqual(result, [(push, None, None)])

    def test_push_include_rule_not_applying_to_repository(self):
        push = {
            'ref': 'refs/heads/master',
            'repository': {'full_name': 'testing'}
        }
        rules = [{
            'filter': 'include',
            'repository': 'user/.*'
        }]

        result = list(response.apply_rules(push, rules))
        self.assertEqual(result, [])

    def test_push_include_rule_applying_to_branch(self):
        push = {
            'ref': 'refs/heads/master',
            'repository': {'full_name': 'testing'}
        }
        rules = [{
            'filter': 'include',
            'branch': 'master'
        }]

        result = list(response.apply_rules(push, rules))
        self.assertEqual(result, [(push, None, None)])

    def test_push_include_rule_not_applying_to_branch(self):
        push = {
            'ref': 'refs/heads/master',
            'repository': {'full_name': 'testing'}
        }
        rules = [{
            'filter': 'include',
            'branch': 'release-.*'
        }]

        result = list(response.apply_rules(push, rules))
        self.assertEqual(result, [])

    def test_push_two_exclude_rules_not_applying(self):
        push = {
            'ref': 'refs/heads/master',
            'repository': {'full_name': 'testing'}
        }
        rules = [{
            'filter': 'exclude',
            'branch': 'release-.*'
        }, {
            'filter': 'exclude',
            'repository': 'testings.*'
        }]

        result = list(response.apply_rules(push, rules))
        self.assertEqual(result, [(push, None, None)])

    def test_push_two_include_rules_applying(self):
        push = {
            'ref': 'refs/heads/master',
            'repository': {'full_name': 'testing'}
        }
        rules = [{
            'filter': 'include',
            'branch': '.*'
        }, {
            'filter': 'include',
            'repository': 'testing'
        }]

        result = list(response.apply_rules(push, rules))
        self.assertEqual(result, [(push, None, None)])

    def test_push_include_rule_branch_and_repository(self):
        push = {
            'ref': 'refs/heads/master',
            'repository': {'full_name': 'testing'}
        }
        rules = [{
            'filter': 'include',
            'repository': 'testing',
            'branch': 'release-.*'
        }]

        result = list(response.apply_rules(push, rules))
        self.assertEqual(result, [])

    def test_push_applying_rule_sets_username(self):
        push = {
            'ref': 'refs/heads/master',
            'repository': {'full_name': 'testing'}
        }
        rules = [{
            'repository': 'testing',
            'username': 'test-user'
        }]

        result = list(response.apply_rules(push, rules))
        self.assertEqual(result, [(push, 'test-user', None)])

    def test_push_applying_rule_sets_channel(self):
        push = {
            'ref': 'refs/heads/master',
            'repository': {'full_name': 'testing'}
        }
        rules = [{
            'repository': 'testing',
            'channel': '#random'
        }]

        result = list(response.apply_rules(push, rules))
        self.assertEqual(result, [(push, None, '#random')])

    def test_push_applying_rule_sets_repository_url(self):
        push = {
            'ref': 'refs/heads/master',
            'repository': {'full_name': 'testing'}
        }
        rules = [{
            'repository_url': 'http://example.com/{repository}'
        }]

        result = list(response.apply_rules(push, rules))
        new_push, _, _ = result[0]

        self.assertEqual(new_push, {
            'ref': 'refs/heads/master',
            'repository': {
                'full_name': 'testing',
                'url': 'http://example.com/testing'
            }
        })

    def test_push_applying_rule_sets_branch_url(self):
        push = {
            'ref': 'refs/heads/master',
            'repository': {'full_name': 'testing'}
        }
        rules = [{
            'branch_url': 'http://example.com/{repository}/tree/{branch}'
        }]

        result = list(response.apply_rules(push, rules))
        new_push, _, _ = result[0]

        self.assertEqual(new_push, {
            'ref': 'refs/heads/master',
            'url': 'http://example.com/testing/tree/master',
            'repository': {
                'full_name': 'testing'
            }
        })

    def test_push_applying_rule_sets_commit_url(self):
        push = {
            'ref': 'refs/heads/master',
            'repository': {'full_name': 'testing'},
            'commits': [
                {'id': 'a697150fd92f21ca186ac0f43cdef6000e6c3d2f'}
            ]
        }
        rules = [{
            'commit_url': 'http://example.com/{repository}/commit/{commit}'
        }]

        result = list(response.apply_rules(push, rules))
        new_push, _, _ = result[0]

        self.assertEqual(new_push, {
            'ref': 'refs/heads/master',
            'repository': {
                'full_name': 'testing'
            },
            'commits': [
                {'id': 'a697150fd92f21ca186ac0f43cdef6000e6c3d2f',
                 'url': ('http://example.com/testing/commit/'
                         'a697150fd92f21ca186ac0f43cdef6000e6c3d2f')
             }]
        })
