import os
import yaml
import datetime

info_file = f'{os.path.dirname(__file__)}/info.yaml'
with open(info_file, 'r') as f:
    data = yaml.safe_load(f)


VERSION = data['version']
RELEASE_DATE = data['release-date']
BUILD = data['build']
DW_WEBSITE = data['dreamwall_website']
DW_GITHUB = data['dreamwall_github_url']
DOC_WEBSITE = data['embarker_documentation_url']
ABOUT = """\
DreamWall Embarker
    Licence MIT
    Version: {version}
    Release date: {release}
    Authors: Olivier Evers, Lionel Brouyère
    build: {build} | {date:%H:%M %d/%m/%Y} | {user}
""".format(
    version=".".join(str(n) for n in VERSION),
    release=RELEASE_DATE,
    build=data['build'],
    date=data['build_datetime'] or datetime.datetime.now(),
    user=data['build_user'])