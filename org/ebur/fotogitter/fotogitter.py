#!/usr/bin/python
# -*- coding: latin-1 -*-

from __future__ import division # damit int / int = float funktioniert
import cv2
import numpy as np
import fotoholer
import os

#gi.require_version('GExiv2', '0.10')
from gi.repository import GExiv2

#===========================================
def height_rows(grd):
    sum = 0
    for r in grd:
        sum += r[0]['h']
    return sum


def calc_thumb_dimensions(image, height_std):
    '''
    Bildmaße ohne Änderung des Seitenverhältnisses auf Standardhöhe umrechnen
    :param height_std: Zielhöhe in px
    :param image: cv2-Bild
    '''
    height, width = image.shape[:2]
    #print(str(height)+'x'+str(width))
    height_thumb = height_std
    width_thumb = int(round(width * height_std / height))
    #print(str(height_thumb)+'x'+str(width_thumb))
    ##thumb = cv2.resize(img,(width_thumb, height_thumb), interpolation = cv2.INTER_CUBIC)
    ##cv2.imwrite('1_thb.jpg',thumb)
    return width_thumb, height_thumb


def get_orientation_angle(exif_orientation_code):
    """
    GEXIV2_ORIENTATION_MIN			= 0,
	GEXIV2_ORIENTATION_UNSPECIFIED	= 0,
	GEXIV2_ORIENTATION_NORMAL		= 1,
	GEXIV2_ORIENTATION_HFLIP		= 2,
	GEXIV2_ORIENTATION_ROT_180		= 3,
	GEXIV2_ORIENTATION_VFLIP		= 4,
	GEXIV2_ORIENTATION_ROT_90_HFLIP	= 5,
	GEXIV2_ORIENTATION_ROT_90		= 6,
	GEXIV2_ORIENTATION_ROT_90_VFLIP	= 7,
	GEXIV2_ORIENTATION_ROT_270		= 8,
	GEXIV2_ORIENTATION_MAX			= 8

	Winkel angepasst für numpy.rot90 (Drehung gegen Uhrzeigersinn)
    """
    if exif_orientation_code == 3:
        return 180
    elif exif_orientation_code in (5,6,7):
        return 270
    elif exif_orientation_code == 8:
        return 90
    else:
        return 0


def rotateImage(image, angle):
    image_center = tuple(np.array(image.shape)/2)
    rot_mat = cv2.getRotationMatrix2D(image_center,angle,1.0)
    result = cv2.warpAffine(image, rot_mat, image.shape,flags=cv2.INTER_LINEAR)
    return result


def build_row(queue, height_std, width_row_std):
    '''
    queue - Liste von Dateinamen
    height_std - angestrebte Höhe der Zeile
    width_row_std - festgelegte Breite der Zeile

    Rückgabe: Liste von Dictionaries. Ein Dictionary beschreibt ein Bild:
        Schlüssel  Inhalt
        --------------------------------------
        n          Dateiname
        w          Breite des Thumbnails in px
        h          Höhe des Thumbnails in px
        a          Winkel
        --------------------------------------
    '''
    def rowwidth(row):
        '''
        Breite der Zeile berechnen

        row: muss eine Liste von Bildinfos sein. Bildinfo = dictionary mit der Breite im Item mit dem Schlüssel 'w'
        '''
        sum = 0
        for item in row:
            sum += item['w']
        return sum

    row = []

    # - wenn Sollbreite der Zeile überschritten ist:
    # -- wenn Abstand zur Sollbreite mit letztem Bild größer ist als ohne letztes Bild
    # ---letztes Bild weg
    # -- sonst:
    # --- so lassen
    # - Zeile durch höher- oder flacher-machen auf Sollbreite bringen (immer Seitenverhältnis der Bilder beachten)

    width_row = 0

    while width_row < width_row_std and len(queue) > 0:
        img = cv2.imread(queue[0]) # index 0 ist immer korrekt, da queue weiter unten gekürzt wird
        exif_orientation = GExiv2.Metadata(queue[0]).get_orientation()
        angle = get_orientation_angle(int(exif_orientation))

        if angle in (90,270):
            width_thumb, height_thumb = calc_thumb_dimensions(np.rot90(img), height_std)
        else:
            width_thumb, height_thumb = calc_thumb_dimensions(img, height_std)

        row.append({'n':queue[0], 'w':width_thumb, 'h':height_thumb, 'a':angle})

        print('fotogitter.build_row:: fuege Bild {0} ({1}x{2}) hinzu'.format(queue[0],width_thumb,height_thumb))

        width_row = rowwidth(row)

        # queue kürzen
        if len(queue) > 1:
            queue = queue[1:]
        else: # Bilder alle
            queue = [] # FIXME: das geht bestimmt auch schöner
        print('fotogitter.build_row:: verbleibende Bilder: {0}'.format(str(queue)))

    if width_row > width_row_std:
        diff1 = abs(width_row_std - width_row) # Überschüssige Breite so wie aktuell
        diff2 = abs(width_row_std - width_row - row[-1]['w']) # fehlende Breite ohne letztes Bild
        # wenn ohne letztes Bild besser, dieses entfernen:
        if diff1 > diff2:
            queue = [row[-1]['n']]+queue # letztes Bild wieder an Spitze der Warteschlange
            row = row[:-1] # letztes Bild aus aktueller Zeile entfernen
            width_row = rowwidth(row) # Zeilenbreite aktualisieren
            print('fotogitter.build_row:: letztes Bild ({0}) wieder entfernt'.format(queue[0]))
            print('fotogitter.build_row:: Zeilenbreite jetzt {0}px'.format(width_row))
        factor = width_row_std/width_row
        # Höhen umrechnen
        for item in row:
            item['h'] = int(round(item['h'] * factor)) # TODO: das kann zu Abweichungen in der Höhe führen (mal auf- mal abrunden?)
            item['w'] = int(round(item['w'] * factor))

        # Zeilenbreite passt jetzt
        print('fotogitter.build_row:: Zeilenbreite: {0}'.format(rowwidth(row)))
    # NOTE: Wenn queue alle ist, und die Zeilenbreite < width_row_std, dann wird hier eine zu schmale Zeile zurückgegeben
    return row, queue

#============================================

def make_grid(imgqueue, height_std = 200, width_row_std = 1000, height_grid_max = 1000):
    grid = []
    row_cur = []

    # Zeile generieren
    height_grid = 0

    while len(imgqueue) > 0 and height_grid < height_grid_max:
        print('fotogitter.make_grid:: naechste Zeile ... ')
        print('fotogitter.make_grid:: verbleibende Bilder: '+str(imgqueue))
        row_cur, imgqueue = build_row(imgqueue, height_std, width_row_std)
        grid.append(row_cur)
        height_grid = height_rows(grid)
        print('fotogitter.make_grid:: Aktuelle Hoehe: '+str(height_grid))

    print('fotogitter.make_grid:: Bildmaße jetzt fertig bestimmt. Bilder werden nun zusammengesetzt ...')

    gridImage = np.zeros((1, width_row_std, 3), np.uint8)

    for r in grid:
        x = 0
        rowImage = np.zeros((r[0]['h'], width_row_std, 3), np.uint8)
        for i in r:
            icv = cv2.imread(i['n'])
            #icv = rotateImage(icv, i['a'])
            icv = np.rot90(icv,i['a']/90)
            print('fotogitter.make_grid:: rotating by {0} degrees'.format(str(i['a'])))
            icv = cv2.resize(icv, (i['w'], i['h']), interpolation = cv2.INTER_CUBIC)
            print('fotogitter.make_grid:: Image size: {0}, x:{1}'.format(str(icv.shape),str(x)))
            #berechnen, ob icv zu groß für den Rest der Zeile ist:
            if x + icv.shape[1] > width_row_std:
                x = width_row_std - icv.shape[1] # einfach vorletztes Bild mit letztem überlappen
            rowImage[0:i['h'], x:x+i['w']] = icv
            x += i['w'] + 1

        gridImage = np.vstack((gridImage,rowImage))

    return gridImage

def set_lockscreen_background(imgpath):
    """
    :param imgpath: Full path of BG-Image
    :return: None
    """
    os.system('gsettings set org.gnome.desktop.screensaver picture-uri file://{0}'.format(imgpath))


def set_desktop_background(imgpath):
    """
    :param imgpath: Full path of BG-Image
    :return: None
    """
    os.system('gsettings set org.gnome.desktop.background draw-background false && gsettings set org.gnome.desktop.background picture-uri file://{0} && gsettings set org.gnome.desktop.background draw-background true'.format(imgpath))


if __name__ == '__main__':
    bgfile = '/home/martin/.cache/grid124589dvtui3vu5.jpg'

    list = fotoholer.get_photo_list('/home/martin/Bilder/Bilder-Lager', ['jpg'], cachefile = 'imagelist.json', cacheMaxAge = 7)

    list = fotoholer.choose_photos(list,50)
    list = fotoholer.cache_photos(list)
    cv2.imwrite(bgfile, make_grid(imgqueue=list, height_std=200, width_row_std=1600, height_grid_max=900))
    set_lockscreen_background(bgfile)
