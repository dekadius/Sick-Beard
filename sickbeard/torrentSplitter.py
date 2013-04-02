# Author: Nic Wolfe <nic@wolfeden.ca>
# URL: http://code.google.com/p/sickbeard/
#
# This file is part of Sick Beard.
#
# Sick Beard is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# Sick Beard is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Sick Beard.  If not, see <http://www.gnu.org/licenses/>.

from name_parser.parser import NameParser, InvalidNameException

import sickbeard

from sickbeard.providers.generic import GenericProvider
from sickbeard import logger, classes, helpers
from sickbeard.common import Quality
from sickbeard import clients

def isSplittingSupported(result):
    if result.provider.providerType != GenericProvider.TORRENT:
        return False
    if sickbeard.TORRENT_METHOD == "blackhole":
        return False
    if not clients.getClientIstance(sickbeard.TORRENT_METHOD)().supportsFilesWanted:
        return False

    return True


def parseFilename(filename):
    # parse the season ep name
    try:
        np = NameParser(True)
        parse_result = np.parse(filename)
        return parse_result
    except InvalidNameException:
        logger.log(u"Unable to parse the filename "+filename+" into a valid episode", logger.WARNING)
        return None

def splitResult(result):
    filesInTorrent = result.provider.getFilesInTorrent(result.id)
    filesWanted = []
    episodesWanted = []
    for fileInTorrent in filesInTorrent:
        parseResult = parseFilename(fileInTorrent)
        fileWanted = False

        if parseResult:
            epNum = parseResult.episode_numbers[0]
            season = parseResult.season_number if parseResult.season_number != None else 1
            #logger.log("Episode number: " +str(epNum))
            fileWanted = result.extraInfo[0].wantEpisode(season, epNum, result.quality)

        if fileWanted:
            episodesWanted.append(epNum)

        filesWanted.append((fileInTorrent, fileWanted))
        #logger.log("FileInTorrent: " + fileInTorrent + ": " + str(fileWanted))

    result.filesWanted = filesWanted

    # remove episodes not wanted from the list of episodes in the result
    episodes = []
    for epObj in result.episodes:
        if epObj.episode in episodesWanted:
            episodes.append(epObj)
    result.episodes = episodes

    return result
