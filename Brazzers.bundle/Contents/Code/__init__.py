import re
import random
import urllib
import urllib2 as urllib
import urlparse
import json
from datetime import datetime
from PIL import Image
from cStringIO import StringIO

VERSION_NO = '1.2013.06.02.1'

def any(s):
    for v in s:
        if v:
            return True
    return False

def Start():
    HTTP.CacheTime = CACHE_1DAY

def capitalize(line):
    return ' '.join([s[0].upper() + s[1:] for s in line.split(' ')])

def tagAleadyExists(tag,metadata):
    for t in metadata.genres:
        if t.lower() == tag.lower():
            return True
    return False

def posterAlreadyExists(posterUrl,metadata):
    for p in metadata.posters.keys():
        Log(p.lower())
        if p.lower() == posterUrl.lower():
            Log("Found " + posterUrl + " in posters collection")
            return True

    for p in metadata.art.keys():
        if p.lower() == posterUrl.lower():
            return True
    return False

class EXCAgent(Agent.Movies):
    name = 'Brazzers'
    languages = [Locale.Language.English]
    accepts_from = ['com.plexapp.agents.localmedia']
    primary_provider = True

    def search(self, results, media, lang):
        
        title = media.name
        if media.primary_metadata is not None:
            title = media.primary_metadata.title

        Log('*******MEDIA TITLE****** ' + str(title))

        # Search for year
        year = media.year
        if media.primary_metadata is not None:
            year = media.primary_metadata.year
            
        encodedTitle = urllib.quote(title)

        searchResults = HTML.ElementFromURL('http://www.brazzers.com/search/all/?q=' + encodedTitle)
        for searchResult in searchResults.xpath('//h2[contains(@class,"scene-card-title")]//a'):
            Log(str(searchResult.get('href')))
            titleNoFormatting = searchResult.get('title')
            curID = searchResult.get('href').replace('/','_')
            lowerResultTitle = str(titleNoFormatting).lower()
            score = 100 - Util.LevenshteinDistance(title.lower(), titleNoFormatting.lower())
            results.Append(MetadataSearchResult(id = curID, name = titleNoFormatting, score = score, lang = lang))
                
        results.Sort('score', descending=True)            

    def update(self, metadata, media, lang):

        Log('******UPDATE CALLED*******')
        zzseries = False
        metadata.studio = 'Brazzers'
        temp = str(metadata.id).replace('_','/')
        url = 'http://www.brazzers.com' + temp
        detailsPageElements = HTML.ElementFromURL(url)

        # Summary
        paragraph = detailsPageElements.xpath('//p[@itemprop="description"]')[0].text_content()
        metadata.summary = paragraph.replace('&13;', '').strip(' \t\n\r"').replace('\n','').replace('  ','') + "\n\n"
        tagline = detailsPageElements.xpath('//span[@class="label-text"]')[0].text_content()
        if tagline == 'ZZ Series':
            zzseries = True
        metadata.tagline = str(tagline)
        metadata.title = detailsPageElements.xpath('//h1')[0].text_content()

        # Genres
        metadata.genres.clear()
        genres = detailsPageElements.xpath('//div[contains(@class,"tag-card-container")]//a')
        genreFilter=[]
        if Prefs["excludegenre"] is not None:
            Log("exclude")
            genreFilter = Prefs["excludegenre"].split(';')

        genreMaps=[]
        genreMapsDict = {}

        if Prefs["tagmapping"] is not None:
            genreMaps = Prefs["tagmapping"].split(';')
            for mapping in genreMaps:
                keyVal = mapping.split("=")
                genreMapsDict[keyVal[0]] = keyVal[1].lower()
        else:
            genreMapsDict = None

        if len(genres) > 0:
            for genreLink in genres:
                genreName = genreLink.text_content().strip('\n').lower()
                if any(genreName in g for g in genreFilter) == False:
                    if genreMapsDict is not None:
                        if genreName in genreMapsDict:
                            if not tagAleadyExists(genreMapsDict[genreName],metadata):
                                metadata.genres.add(capitalize(genreMapsDict[genreName]))
                        else:
                            if not tagAleadyExists(genreName,metadata):
                                metadata.genres.add(capitalize(genreName))
                    else:
                        metadata.genres.add(capitalize(genreName))

        if not zzseries:
            date = detailsPageElements.xpath('//aside[contains(@class,"scene-date")]')[0].text_content()
            date_object = datetime.strptime(date, '%B %d, %Y')
            metadata.originally_available_at = date_object
            metadata.year = metadata.originally_available_at.year
        else:
            for wrapper in detailsPageElements.xpath('//div[@class="release-card-wrap"]'):
                Log('wrapper')
                cardTitle = wrapper.xpath('.//div[@class="card-image"]//a')[0].get('title')
                Log(cardTitle)
                if cardTitle.lower() == metadata.title.lower():
                    Log('match')
                    date = detailsPageElements.xpath('..//time')[0].text_content()
                    date_object = datetime.strptime(date, '%B %d, %Y')
                    metadata.originally_available_at = date_object
                    metadata.year = metadata.originally_available_at.year 
                    metadata.roles.clear()
                    metadata.collections.clear()
                    starring = wrapper.xpath('.//div[@class="model-names"]//a')
                    for member in starring:
                        role = metadata.roles.new()
                        role.actor = member.get('title').strip()
                        metadata.collections.add(member.get('title').strip())
                    p = wrapper.xpath('.//div[@class="card-image"]//img')[0].get('src')
                    Log(p)
                    metadata.posters[p] = Proxy.Preview(HTTP.Request(p, headers={'Referer': 'http://www.google.com'}).content, sort_order = 1)
                        
        # Starring/Collection
        # Create a string array to hold actors
        maleActors=[]
        
        # Refresh the cache every 50th query
        if('cache_count' not in Dict):
            Dict['cache_count'] = 0
            Dict.Save()
        else:
            cache_count = float(Dict['cache_count'])
            if(cache_count == 50):
                Log(str(cache_count))
                Dict.Reset()
            else:
                Dict['cache_count'] = str(cache_count + 1)
                Dict.Save()
                Log(str(cache_count))
          
        if('actors' not in Dict):
            Log('******NOT IN DICT******')
            maleActorHtml = None
            maleActorHtml = HTML.ElementFromURL('http://www.data18.com/sys/get3.php?t=2&network=1&request=/sites/brazzers/')

            # Add missing actors
            for actor in maleActorHtml.xpath('//option'):
                itemString = actor.text_content()
                actorArray = itemString.split("(")
                try:
                    # Add item to array
                    actor = actorArray[0].strip()
                    maleActors.append(actor)
                except: pass
            Dict['actors'] = maleActors
            Dict.Save()
        else:
            Log('******IN DICT******')
            maleActors = Dict['actors']

        if Prefs['excludeactor'] is not None:
            addActors = Prefs['excludeactor'].split(';')
            for a in addActors:
                maleActors.append(a)
      
        #starring = None
        if not zzseries:
            metadata.roles.clear()
            metadata.collections.clear()
            starring = detailsPageElements.xpath('//p[contains(@class,"related-model")]//a')

            for member in starring:
                # Check if member exists in the maleActors list as either a string or substring
                if any(member.text_content().strip() in m for m in maleActors) == False:
                    role = metadata.roles.new()
                    # Add to actor and collection
                    role.actor = member.text_content().strip()
                    metadata.collections.add(member.text_content().strip())

        #Rating
        #try:
            #likes = detailsPageElements.xpath('//span[@class="like"]')[0].text_content().strip()
            #dislikes = detailsPageElements.xpath('//span[@class="dislike"]')[0].text_content().strip()
            #if(likes != 0 and dislikes != 0):
                #total = float(likes) + float(dislikes)
                #rating = float(likes) / total * 10
                #metadata.rating = rating
        #except:pass

        #Posters
        if not zzseries:
            i = 1
            for poster in detailsPageElements.xpath('//a[@rel="preview"]'):
                posterUrl = poster.get('href').strip()
                thumbUrl = detailsPageElements.xpath('//img[contains(@src,"thm")]')[i-1].get('src')
                if not posterAlreadyExists(posterUrl,metadata):            
                    #Download image file for analysis
                    img_file = urllib.urlopen(posterUrl)
                    im = StringIO(img_file.read())
                    resized_image = Image.open(im)
                    width, height = resized_image.size

                    #Add the image proxy items to the collection
                    if(width == 533):
                        # Item is a poster
                        metadata.posters[posterUrl] = Proxy.Preview(HTTP.Request(thumbUrl, headers={'Referer': 'http://www.google.com'}).content, sort_order = i)
                    if(width == 800):
                        # Item is an art item
                        metadata.art[posterUrl] = Proxy.Preview(HTTP.Request(thumbUrl, headers={'Referer': 'http://www.google.com'}).content, sort_order = i)
                    i += 1
        else:
            
            background = detailsPageElements.xpath('//*[@id="trailer-player"]/img')[0].get('src')
            Log(background)
            metadata.art[background] = Proxy.Preview(HTTP.Request(background, headers={'Referer': 'http://www.google.com'}).content, sort_order = 1)
