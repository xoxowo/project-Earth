
from pytimekr import pytimekr
import calendar
import datetime
import pandas
import re
import mysql.connector
import my_settings

from django.utils      import timezone
from django.db.models  import Min, Max

from core.emunutils   import DayEnum
from detection.models import Detection

# ./my_db_settings.py
mydb     = my_settings.mydb
mycursor = mydb.cursor()

def save_data_in_MYSQL(data):
    try: 
        '''
        data에 담긴 데이터 형식
        {'cam_id': 1,
        'datetime': '2022-08-31T17:01:11+0900',
        'detection_count': 2,
        'detection_information': [{ 'detection_type': 'truck',
                                    'height': 182,
                                    'id': 'truck_144',
                                    'state': 'travel',
                                    'width': 292,
                                    'x': 887,
                                    'y': 493},
                                  { 'detection_type': 'wheel_loader',
                                    'height': 277,
                                    'id': 'wheel_loader-000',
                                    'state': 'load',
                                    'width': 226,
                                    'x': 407,
                                    'y': 854}]}
        '''
        cam_id                 = data['cam_id']
        detection_count        = data['detection_count']
        datetime               = data['datetime']   # "2022-08-18T11:45:41+0900"
        detection_informations = data['detection_information']
 
        datetime_split = re.split('[T|+]',datetime) 
        datetime       = datetime_split[0] + ' ' + datetime_split[1]  # "2022-08-18 11:45:41" MYSQL에 저장가능한 형태 

        for i in range(detection_count):
            detection_information = detection_informations[i]

            detection_type_name = detection_information['detection_type']
            serial_number       = detection_information['id']
            x                   = detection_information['x']
            y                   = detection_information['y']
            width               = detection_information['width']
            height              = detection_information['height']
            equipment_state     = detection_information['state']

            check_list = [x, y, width, height]
            for i in check_list:
                int(i)  # 숫자가 아니면 ValueError 발생
                if (not type(i) == int) or (int(i) < 0):  # 양의 정수가 아니면 경고 문구 출력 후 코드는 계속 진행
                    print(datetime, '%s is not positive integer!' %i)

            mycursor.execute('SELECT id FROM detection_types WHERE name=%s', (detection_type_name,))     
            detection_type_id, = mycursor.fetchone()  

            mycursor.execute('SELECT id FROM states WHERE equipment_state=%s', (equipment_state,))
            state_id, = mycursor.fetchone()

            if detection_type_name == 'truck':
                equipment_id = None
            else :
                mycursor.execute('SELECT id FROM equipment WHERE serial_number=%s', (serial_number,))
                equipment_id, = mycursor.fetchone()

            PROGRESS_DETECTION = 'wheel_loader_000' # 이걸로 가정
            START_X            = 200                # 작업구역 시작 x좌표
            TURNING_X          = 1080               # 작업구역 끝 x좌표
            PROGRESS_PER_ONE   = 20/20              # y축 방향 편도 1회당 공정률(%) = x축 방향 왕복 1회 공정률(%) / y축 방향 총 편도 반복횟수
                                ## 여기서 x축 방향 왕복 1회 공정률이 20 미만으로 떨어지면, progress가 정수로 모델링 되어 있어서 코드 수정 필요함
            START_Y            = 120                # 작업구역 시작 y좌표
            TURNING_Y          = 620                # 작업구역 끝 y좌표
            INITIAL_PROGRESS   = 0                  # 작업 중간부터 detect 시작했을 경우 초기 공정률값 설정 가능
            ERROR_RANGE        = 30
            ### 상수값들 core/utils.py 에 저장해두고 불러오는게 더 좋으려나?

            if serial_number == PROGRESS_DETECTION:  
                last   = Detection.objects.filter(serial_number=PROGRESS_DETECTION, area_id=cam_id).last()
                if START_X <= x <= TURNING_X:
                    last_y        = last.y  if last  else START_Y  # 첫 감지 시 last_y를 START_POINT로 설정하여 작업구역 도착 전 이동은 예외처리 가능
                    last_progress = last.progress if last and last.progress else INITIAL_PROGRESS
                    
                    detection_last_progress = Detection.objects.filter(progress=last_progress)
                    if not detection_last_progress:  ## 첫 감지 시 예외처리
                        progress = last_progress
                    if last_y <= TURNING_Y < y and \
                            y - detection_last_progress.values('progress').annotate(min_y=Min('y'))[0]['min_y'] > ERROR_RANGE:
                        progress = last_progress + PROGRESS_PER_ONE   
                    elif y < START_Y <= last_y and \
                            detection_last_progress.values('progress').annotate(max_y=Max('y'))[0]['max_y'] - y > ERROR_RANGE:
                        progress = last_progress + PROGRESS_PER_ONE
                    else:
                        progress = last_progress
                else:
                    progress = last.progress if last and last.progress else INITIAL_PROGRESS
                print('######## 공정률: %s, y값: %s' %(progress,y)) 
            else :
                progress = None                
            
            sql = '''INSERT 
                INTO detection (x,y,width,height,serial_number,datetime,area_id,detection_type_id,state_id, equipment_id, progress) 
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                '''
            val = (x, y, width, height, serial_number, datetime, cam_id, detection_type_id, state_id, equipment_id, progress)
            mycursor.execute(sql,val)

            mydb.commit()
          
        print('>>> %s에 정상적으로 %s 데이터 %s개를 저장했습니다.' % (timezone.now(), datetime, detection_count))
   

    except KeyError as e :   # data의 키값 오류일 때
        print(e, '\n', datetime, 'KEY_ERROR:')
    except ValueError as e :
        print(e, '\n', datetime, '%s VALUE_ERROR' %i)
    except (TypeError, mysql.connector.errors.InternalError) as e :   # 참조키 관련 DB에 없는 value가 들어왔을 때 
        print(e, '\n', datetime + ' ' + str(i+1) + 'st Equipment Does Not Exist in DB')
    except Exception as e:
        print(datetime, '새로운 예외 발생:', e)


WEEKDAY_WORKING_TIME  = 8 * 60 * 60 # 초 단위
SATURDAY_WORKING_TIME = 4 * 60 * 60 # 초 단위
RED_DAY_WORKING_TIME  = 0 

red_days = lambda year : pytimekr.holidays(year) 

def calculate_working_time(today, select):
    if select == 'daily':
        dates = [today]     

    elif select == 'weekly':
        weekday     = today.weekday() # 0:월, 1:화, 2:수, 3:목, 4:금, 5:토, 6:일
        last_monday = today - datetime.timedelta(days=weekday)
        dates       = pandas.date_range(last_monday, periods=7)

    elif select == 'monthly':
        end_day = calendar.monthrange(today.year,today.month)[1] 
        dates = [today.replace(day=date) for date in range(1, end_day+1)]

    working_time = 0
    for date in dates:
        if  date.date() in red_days(date.year) or date.isoweekday() == DayEnum.SUN.value:
            working_time += RED_DAY_WORKING_TIME
        elif date.isoweekday() == DayEnum.SAT.value:
            working_time += SATURDAY_WORKING_TIME
        else:
            working_time += WEEKDAY_WORKING_TIME

    return working_time


PROGRESS_DETECTION = 'wheel_loader_000' # 이걸로 가정
START_X            = 200                # 작업구역 시작 x좌표
TURNING_X          = 1080               # 작업구역 끝 x좌표
PROGRESS_PER_ONE   = 20/20              # y축 방향 편도 1회당 공정률(%) = x축 방향 왕복 1회 공정률(%) / y축 방향 총 편도 반복횟수
                    ## 여기서 x축 방향 왕복 1회 공정률이 20 미만으로 떨어지면, progress가 정수로 모델링 되어 있어서 코드 수정 필요함
START_Y            = 120                # 작업구역 시작 y좌표
TURNING_Y          = 620                # 작업구역 끝 y좌표
INITIAL_PROGRESS   = 0                  # 작업 중간부터 detect 시작했을 경우 초기 공정률값 설정 가능
ERROR_RANGE        = 30