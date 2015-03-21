
"""Respond to notifications"""

import re
import logging

from git_slack import slack

logger = logging.getLogger(__name__)


def message_from_push(push, slack_username=None, slack_channel=None):
    """Return response message from Git push object"""

    # No messages on branch delete
    if push['deleted']:
        logger.info('Push is a delete; no message generated.')
        return None

    m = re.match(r'^refs/heads/(.*)$', push['ref'])
    if not m:
        logger.info('Push is not to a branch; no message generated.')
        return None

    if len(push['commits']) == 0:
        logger.info('Push contains no new commits; no message generated.')
        return None

    branch = m.group(1)
    if 'url' in push:
        branch_link = slack.Link(push['url'], branch)
    else:
        branch_link = branch

    repo_name = push['repository']['full_name']
    if 'url' in push['repository']:
        repo_link = slack.Link(push['repository']['url'], repo_name)
    else:
        repo_link = repo_name

    logger.info('Push received for {}, branch: {}'.format(repo_name,
                                                          branch))

    commit_count = len(push['commits'])
    commits_text = ('one new commit' if commit_count == 1 else
                    '{} new commits'.format(commit_count))

    fallback = '[{}:{}] {}'.format(repo_name, branch, commits_text)
    pretext = slack.Markup('[{}:{}] {}:').format(
        repo_link, branch_link, commits_text)
    commits = []
    for commit in push.get('commits', []):
        abbrev = commit['id'][:7]
        if 'url' in commit:
            commit_link = slack.Link(commit['url'], abbrev)
        else:
            commit_link = abbrev
        commits.append(slack.Markup('{}: {} - {}').format(
            commit_link, commit['message'], commit['author']['name']))
    attachment = slack.Attachment(fallback=fallback,
                                  pretext=pretext,
                                  color='#4183c4',
                                  text=slack.Markup('\n').join(commits))
    message = slack.Message(attachments=[attachment],
                            username=slack_username,
                            channel=slack_channel)

    return message
