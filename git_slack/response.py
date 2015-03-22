
"""Respond to notifications"""

import re
import logging

from git_slack import slack

logger = logging.getLogger(__name__)


class RulesError(Exception):
     """Error while applying rules"""


def apply_rules(push, rules, slack_username=None, slack_channel=None):
    """Apply rules and yield push, username, channel to be sent"""

    m = re.match(r'^refs/heads/(.*)$', push['ref'])
    if not m:
        logger.info('Push is not to a branch; no message generated.')
        return

    branch = m.group(1)

    for rule_id, rule in enumerate(rules):
        if ('filter' in rule and
                rule['filter'] not in ('include', 'exclude')):
            raise RulesError('Filter attribute of rule must be include'
                             ' or exclude')

        exclude = rule.get('filter', None) == 'exclude'
        include = rule.get('filter', None) == 'include'

        all_match = True

        # Filter based on repository
        if 'repository' in rule:
            match = re.match(rule['repository']+r'\Z',
                             push['repository']['full_name'])
            all_match = match and all_match
            if match and exclude or not match and include:
                logger.info('Rule #{}: Filter based on repository'.format(
                    rule_id))
                return

        # Filter based on branch
        if 'branch' in rule:
            match = re.match(rule['branch']+r'\Z', branch)
            all_match = match and all_match
            if match and exclude or not match and include:
                logger.info('Rule #{}: Filter based on branch'.format(rule_id))
                return

        if all_match:
            # Update Slack settings if matching
            if 'username' in rule:
                slack_username = rule['username']
            if 'channel' in rule:
                slack_channel = rule['channel']

            # Update repository URL if matching
            if 'repository_url' in rule:
                repo_url = rule['repository_url'].format(
                    repository=push['repository']['full_name'])
                if repo_url != '':
                    push['repository']['url'] = repo_url
                else:
                    push['repository'].pop('url', None)

            # Update branch URL if matching
            if 'branch_url' in rule:
                branch_url = rule['branch_url'].format(
                    repository=push['repository']['full_name'],
                    branch=branch)
                if branch_url != '':
                    push['url'] = branch_url
                else:
                    push.pop('url', None)

            # Update commit URLs if matching
            if 'commit_url' in rule:
                for commit in push['commits']:
                    commit_url = rule['commit_url'].format(
                        repository=push['repository']['full_name'],
                        branch=branch, commit=commit['id'])
                    if commit_url != '':
                        commit['url'] = commit_url
                    else:
                        commit.pop('url', None)

    yield push, slack_username, slack_channel


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
