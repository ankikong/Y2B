from configparser import ConfigParser

def _run(file):
    parser = ConfigParser()
    content = parser.read(file, encoding="utf8")
    return parser, content

parser = _run("setting.conf")[0]
channel, channels = _run("channel.conf")
