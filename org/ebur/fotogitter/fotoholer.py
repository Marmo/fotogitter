#!/usr/bin/python
# -*- coding: latin-1 -*-

from __future__ import division # damit int / int = float funktioniert
import os
import shutil
import random
import json
import time


def get_photo_list(rootpath, ext = ('jpg','png','jpeg'), cachefile = 'imagelist.json', cacheMaxAge = 0):
    """
    :param rootpath: Pfad, der rekursiv durhsucht wird
    :param ext: Nur Dateien mit einer dieser Erweiterungen werden gelistet
    :param cachefile: Datei, in der die Dateiliste gespeichert werden soll
    :param cache: Wahrheitswert, ob die Dateiliste gespeichert werden soll
    :return: Liste mit passenden Fotos
    """
    list = []

    cacheMaxAge *= 86400 # in Sekunden konvertieren
    try:
        cacheAge = time.time() - os.stat(cachefile).st_mtime
        print('fotoholer.get_photo_list:: Photo-List cache in {0} is {1} seconds old.'.format(cachefile, cacheAge))
    except OSError as e:
        cacheAge, cacheMaxAge = 1,0
        print('fotoholer.get_photo_list:: Photo-List cache in {0} unreadable/not existent. It must be a thousand years old.'.format(cachefile))
        print('fotoholer.get_photo_list:: {0}'.format(e))

    if cacheAge > cacheMaxAge:
        print('fotoholer.get_photo_list:: This is too old. Refreshing list ...')
        # Dateiliste generieren
        for root, dummy, files in os.walk(rootpath, topdown=False):
            for name in files:
                if name.split('.')[-1].lower() in ext:
                    imgfile = os.path.join(root, name)
                    list.append(imgfile)
                    print('fotoholer.get_photo_list:: Found {0}'.format(imgfile))

        # Cache schreiben
        try:
            f = open('imagelist.json','w')
            json.dump(list, f)
        except IOError as e:
            print('fotoholer.get_photo_list:: ERROR: Unable to write list to {0}'.format(cachefile))
            print(str(e))
        else:
            f.close()
    else:
        print('fotoholer.get_photo_list:: This is recent enough. Reading list from cache ...')
        list = get_photo_list_cached(cachefile)

    return list


def get_photo_list_cached(cachefile):
    """
    :param cachefile: json-Datei mit Fotopfaden
    :return: Liste mit Fotopfaden
    """
    list = []

    try:
        f = open(cachefile, 'r')
        list = json.load(f)
    except IOError as e:
            print('fotoholer.get_photo_list_cached:: ERROR: Unable to read from list {0}'.format(cachefile))
            print(str(e))
    else:
        f.close()

    return list


def choose_photos(list, number):
    """
    :param list: Liste mit Fotos
    :param number: Anzahl gewünschter Fotos
    :return: Liste mit zufällig ausgewählten Fotos
    """
    if len(list) <= number:
        return list
    else:
        smalllist = []
        while number > 0:
            smalllist.append(random.choice(list))
            # TODO: Verhindern, dass ein Bild mehrmals verwendet wird. Index zufällig bestimmen und item aus list entfernen
            number -= 1
        return smalllist

def cache_photos(list, cachedir='./cache'):
    """
    Ignoriert Unterverzeichnisse im cachedir
    :param list: Liste der zu holenden Fotos
    :param cachedir: Zielort
    :return: Liste der Bilder im Cache
    """
    #cache leeren
    root, dummy, files = os.walk(cachedir, topdown=True).next()
    for name in files:
        os.remove(os.path.join(root, name))
        print('fotoholer.cache_photo:: deleting {0}'.format(os.path.join(root, name)))

    #Bilder aus Liste in Cache kopieren
    for src in list:
        print('fotoholer.cache_photo:: caching {0}'.format(src))
        shutil.copy(src, cachedir)

    root, dummy, files = os.walk(cachedir, topdown=True).next()
    list_cached = [os.path.join(root, name) for name in files]

    return list_cached





if __name__ == '__main__':
    l = get_photo_list('/home/martin/Bilder/00_Eingang', ['jpg'])
    s = choose_photos(l,5)
    print(str(s))
    photos = cache_photos(s)
    print(str(photos))