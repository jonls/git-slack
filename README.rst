Git-Slack
============

A daemon to post Git push information to Slack. It uses AMQP to obtain
Git push information. The information must be sent to an AMQP server from
the ``post-receive`` hook of the Git repositories. See
`jonls/amqp-post-receive`_ for an example ``post-receive`` hook.

.. _jonls/amqp-post-receive: https://github.com/jonls/amqp-post-receive

Configuration
-------------

The configuration is read from a simple YAML file. See `config-example.yaml`_
for an example. To load the configuration run::

   $ git-slack --config config.yaml

.. _config-example.yaml: config-example.yaml
