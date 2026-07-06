"""
raspberry_pi/generate_markers.py
================================
توليد صور علامات ArUco للطباعة (PNG لكل علامة).

التشغيل:
  python3 generate_markers.py
ينتج: marker_1.png ... marker_5.png  (اطبعها بحجم ~15x15 سم والصقها)

التوزيع حسب الخريطة:
  1 = القسم 1   |  2 = القسم 2  |  3 = القسم 3
  4 = المدخل    |  5 = المخرج
"""
import cv2

ARUCO_DICT = cv2.aruco.getPredefinedDictionary(cv2.aruco.DICT_4X4_50)
MARKER_IDS = [1, 2, 3, 4, 5]
SIZE_PX = 600          # دقة الصورة (تكفي لطباعة 15 سم بجودة ممتازة)
BORDER_BITS = 1

for marker_id in MARKER_IDS:
    img = cv2.aruco.generateImageMarker(ARUCO_DICT, marker_id, SIZE_PX, borderBits=BORDER_BITS)
    # إطار أبيض حول العلامة (ضروري لموثوقية الاكتشاف)
    img = cv2.copyMakeBorder(img, 60, 60, 60, 60, cv2.BORDER_CONSTANT, value=255)
    filename = f"marker_{marker_id}.png"
    cv2.imwrite(filename, img)
    print("saved", filename)
