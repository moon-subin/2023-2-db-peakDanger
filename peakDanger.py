import sqlite3
import requests
from datetime import datetime
import math
import config

conn = sqlite3.connect("C:\\Users\\subin\\Documents\\embedded\\2023-2\\database\\dangerInfo.db")
cursor = conn.cursor()

# 테이블 생성
def createTable():
    # 사용자 (User)
    createUserTablequery = """
        CREATE TABLE IF NOT EXISTS User (
            uID INTEGER PRIMARY KEY AUTOINCREMENT,
            uName TEXT
        );
    """
    cursor.execute(createUserTablequery)

    # 방문한 봉우리 (VisitPeak)
    createVisitPeakTablequery = """
        CREATE TABLE IF NOT EXISTS VisitPeak (
            hikeID INTEGER PRIMARY KEY AUTOINCREMENT,
            uID INTEGER,
            peakName TEXT,
            date DATE,
            FOREIGN KEY (uID) REFERENCES User(uID)
        );
    """
    cursor.execute(createVisitPeakTablequery)

    # 방문한 위험 지역 (DangerPlc)
    createDangerPlcTablequery = """
        CREATE TABLE IF NOT EXISTS DangerPlc (
            hikeID INTEGER,
            lat REAL,
            lot REAL,
            plcNm TEXT,
            explnCn TEXT,
            wayLat REAL DEFAULT NULL,
            wayLot REAL DEFAULT NULL,
            way TEXT DEFAULT NULL,
            FOREIGN KEY (hikeID) REFERENCES VisitPEAK(hikeID)
        );
    """
    cursor.execute(createDangerPlcTablequery)
    conn.commit()


# 방문한 봉우리 삽입
def insertVisitPeak(uID, peakName):
    currentDate  = datetime.now().strftime("%Y-%m-%d")
    insertVisitPeakquery = """
        INSERT INTO VisitPeak (uID, peakName, date) VALUES (?, ?, ?);
    """
    cursor.execute(insertVisitPeakquery, (uID, peakName, currentDate))
    conn.commit()

# 방문한 위험 지역 삽입
def insertDangerPlc(hikeID, lat, lot, plcNm, explnCn):
    insertDangerPlcquery = """
        INSERT INTO DangerPlc (hikeID, lat, lot, plcNm, explnCn) VALUES (?, ?, ?, ?, ?);
    """
    cursor.execute(insertDangerPlcquery, (hikeID, lat, lot, plcNm, explnCn))
    conn.commit()

# 사용자 아이디 불러오기
def getUIDbyName(uName):
    getUIDbyNamequery = "SELECT uID FROM User WHERE uName = ?"
    cursor.execute(getUIDbyNamequery, (uName,))
    result = cursor.fetchone()
    conn.commit()
    return result[0]

# 사용자의 등산번호 불러오기
def getLatestHikeIDbyUID(uID):
    getLatestHikeIDbyUIDquery = "SELECT hikeID FROM VisitPeak WHERE uID = ?"
    cursor.execute(getLatestHikeIDbyUIDquery, (uID,))
    result = cursor.fetchone()
    conn.commit()
    return result[0]

# 우회 경로 업데이트
def updateWaybyDangerPlc(way_lat, way_lot, way, hikeID):
    updateWaybyDangerPlcquery = """
        UPDATE DangerPlc
        SET wayLat = ?, wayLot = ?, way = ?
        WHERE hikeID = ?;
    """
    cursor.execute(updateWaybyDangerPlcquery, (way_lat, way_lot, way, hikeID,))
    conn.commit()

def getPeakDangerousAreas(peakname, peakstate, key):
    endpoint = "http://apis.data.go.kr/B553662/dangerInfoService/getDangerInfoList"
    url = f"{endpoint}?serviceKey={key}&type=json&numOfRows=100&pageNo=1&srchFrtrlNm={peakname}&srchPlaceTpeCd={peakstate}"

    # API 요청
    res = requests.get(url)
    return res

if __name__ == '__main__':
    key = config.key

    uName = input('사용자 이름: ')              # subin
    peakname = input('현재 봉우리: ')           # 천왕봉
    latitude = float(input('현재 위도: '))      # 35.151558
    longitude = float(input('현재 경도: '))     # 127.864037

    peakstateDanger = "DANGER"

    createTable()

    # uID select
    uID = getUIDbyName(uName)
    
    hikeID = None

    responseDanger = getPeakDangerousAreas(peakname, peakstateDanger, key)
    print('danger res: ', responseDanger)    

    if responseDanger.status_code == 200:
        responseDanger_body = responseDanger.json()['response']['body']
        items = responseDanger_body['items']['item']

        # 위험 지역 확인
        for item in items:
            if item['lat'] == latitude and item['lot'] == longitude:
                # 방문한 봉우리 추가
                insertVisitPeak(uID=uID, peakName=item['frtrlNm'])

                # 현재 위험 지역 추가
                hikeID = getLatestHikeIDbyUID(uID)
                insertDangerPlc(hikeID=hikeID, lat=item['lat'], lot=item['lot'], plcNm=item['plcNm'], explnCn=item['explnCn'])


    peakstateSign = "SIGN"
    peakstateSign = getPeakDangerousAreas(peakname, peakstateSign, key)
    print('sign res: ', peakstateSign)    

    if peakstateSign.status_code == 200:
        peakstateSign_body = peakstateSign.json()['response']['body']
        items = peakstateSign_body['items']['item']

        closest_item = None
        min_distance = float('inf')

        way = None

        for item in items:
            distance = math.sqrt((item['lat'] - latitude)**2 + (item['lot'] - longitude)**2)

            if distance < min_distance:
                min_distance = distance
                closest_item = item

        if closest_item is not None:
            way_lat = closest_item['lat']
            way_lot = closest_item['lot']

        else:
            print("가장 가까운 지역을 찾을 수 없습니다.")

        # 이동 방향
        if latitude > closest_item['lat']:
            way = 'toSouth'
        elif latitude < closest_item['lat']:
            way = 'toNorth'
        elif longitude > closest_item['lot']:
            way = 'toWest'
        elif longitude < closest_item['lot']:
            way = 'toEast'

        print(way)
        updateWaybyDangerPlc(way_lat=way_lat, way_lot=way_lot, way=way, hikeID=hikeID)

# 사용이 끝났으면 연결 닫기
conn.close()