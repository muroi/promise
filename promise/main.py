import sys, pbr.version
from cliff import app
from cliff import commandmanager

version_info = pbr.version.VersionInfo('promise')

class PromiseClient(app.App):
    def __init__(self):
        super(PromiseClient, self).__init__(
            description='Promise demo CLI',
            version=version_info,
            command_manager=commandmanager.CommandManager('promise.cli'),
            deferred_help=True)


def main(argv=sys.argv[1:]):
    return PromiseClient().run(argv)
