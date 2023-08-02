import json
import os
from flask import Flask, request, make_response, jsonify
from slacker import Slacker
import requests

token = os.environ.get('TOKEN')
access_token = os.environ.get('ACCESS_TOKEN')

slack = Slacker(token)

app = Flask(__name__)


def get_message_from_server(url):
    headers = {
        'accept': '*/*',
        "Authorization": "Bearer " + token,
        "Content-Type": "application/json",
    }

    return requests.get(url, headers=headers)


def post_message(token, channel, text):
    response = requests.post("https://slack.com/api/chat.postMessage",
                             headers={"Authorization": "Bearer " + token},
                             data={"channel": channel, "text": text})
    print(response)


def handle_subscribe(query, channel):
    if query[0] == "승인":
        request_url = "https://repick.seoul.kr/api/slack/subscribe/add"
    elif query[0] == "거절":
        request_url = "https://repick.seoul.kr/api/slack/subscribe/deny"
    else:
        post_message(token, channel, "승인 또는 거절 중 하나여야 합니다.")
        return "잘못된 입력입니다."

    # 정상적 접근 : 서버로 요청
    requests.post(request_url,
                  headers={"Authorization": "Bearer " + token, "Content-Type": "application/json"},
                  json={
                      "orderNumber": query[1]
                  })


def handle_order(query, channel):
    request_url = "https://repick.seoul.kr/api/slack/order/update"
    if query[1] == "입금완료":
        state = "PREPARING"
    elif query[1] == "배송중":
        state = "DELIVERING"
    elif query[1] == "배송완료":
        state = "DELIVERED"
    elif query[1] == "취소됨":
        state = "CANCELED"
    else:
        post_message(token, channel, "상태는 '입금완료', '배송중', '배송완료', '취소됨' 중 하나여야 합니다.")
        return "잘못된 입력입니다."

    requests.post(request_url,
                  headers={"Authorization": "Bearer " + token, "Content-Type": "application/json"},
                  json={
                      "orderNumber": query[0],
                      "sellState": state
                  })


def handle_sell_order(query, channel):
    request_url = "https://repick.seoul.kr/api/slack/sell/update"
    if query[1] == "배달됨":
        state = "DELIVERED"
    elif query[1] == "취소됨":
        state = "CANCELED"
    elif query[1] == "처리됨":
        state = "PUBLISHED"
    else:
        post_message(token, channel, "상태는 '배달됨', '취소됨', '처리됨' 중 하나여야 합니다.")
        return "잘못된 입력입니다."

    requests.post(request_url,
                  headers={"Authorization": "Bearer " + token, "Content-Type": "application/json"},
                  json={
                      "orderNumber": query[0],
                      "sellState": state
                  })


def handle_home_fitting(query, channel):
    request_url = "https://repick.seoul.kr/api/slack/homefitting/update"
    post_message(token, channel, "홈피팅 관리는 미구현 기능입니다. 스웨거를 통한 신청 바랍니다.")


def handle_expense_settlement(query, channel):
    request_url = "https://repick.seoul.kr/api/slack/settlement/update"

    if len(query) > 1:
        post_message(token, channel, "잘못된 입력입니다. 정산 관리 양식은 '정산 [상품번호]입니다.")
        return "잘못된 입력입니다."

    requests.post(request_url,
                  headers={"Authorization": "Bearer " + token, "Content-Type": "application/json"},
                  json={
                      "productNumber": query[0],
                  })


def handle_help(query, channel):
    if query[0] == "구독":
        post_message(token, channel, "구독 관리 명령어는 '구독 [승인/거절] [주문번호]'입니다.")
    if query[0] == "판매":
        post_message(token, channel, "판매 관리 명령어는 '판매 [주문번호] [배달됨/취소됨/처리됨]'입니다.")
    if query[0] == "구매":
        post_message(token, channel, "구매 관리 명령어는 '구매 [주문번호] [입금완료/배송중/배송완료/취소됨]'입니다.")
    if query[0] == "홈피팅":
        post_message(token, channel, "홈피팅 관리 명령어는 '홈피팅은 아직 미구현 기능입니다.")
    if query[0] == "정산":
        post_message(token, channel, "정산 관리 명령어는 '정산 [상품번호]'입니다.")
    else:
        post_message(token, channel, "도움말 관리 명령어는 '도움말 [구독/판매/구매/홈피팅/정산]'입니다.")


def handle_other_msg(query, channel):
    if query[0] == "농담":
        post_message(token, channel, "그런건 없어요~")
    elif query[0] == "테스트":
        post_message(token, channel, "피키 v1.3 ")
    elif query[0] == "뭐해":
        post_message(token, channel, "일중입니다. 당신이랑 대화하는것도 일입니다.")
    elif query[0] == "찬혁":
        post_message(token, channel, "찬혁님은 제 주인님입니다. 업무 자동화를 위해 저를 만드셨어요.")
    elif query[0] == "피키":
        post_message(token, channel, "피키는 제 이름이에요. 저는 리픽 서비스를 위해 밤낮 없이 일한답니다.")
    else:
        post_message(token, channel, "잘못된 입력입니다. 명령어를 알고싶다면 '도움말'을 입력하세요.")
        return "잘못된 입력입니다."


def handle_msg(user_query, channel):
    msg = user_query.split()
    if msg[0] == "구독":
        if len(msg) == 1:
            post_message(token, channel, "구독 관리 명령어는 '구독 [승인/거절] [주문번호]'입니다.")
        else:
            handle_subscribe(msg[1:], channel)
    elif msg[0] == "판매":
        if len(msg) == 1:
            post_message(token, channel, "판매 관리 명령어는 '판매 [주문번호] [배달됨/취소됨/처리됨]'입니다.")
        else:
            handle_sell_order(msg[1:], channel)
    elif msg[0] == "구매":
        if len(msg) == 1:
            post_message(token, channel, "구매 관리 명령어는 '구매 [주문번호] [입금완료/배송중/배송완료/취소됨]'입니다.")
        else:
            handle_order(msg[1:], channel)
    elif msg[0] == "홈피팅":
        if len(msg) == 1:
            post_message(token, channel, "홈피팅 관리 명령어는 '홈피팅은 아직 미구현 기능입니다.")
        else:
            handle_home_fitting(msg[1:], channel)
    elif msg[0] == "정산":
        if len(msg) == 1:
            post_message(token, channel, "정산 관리 명령어는 '정산 [상품번호]'입니다.")
        else:
            handle_expense_settlement(msg[1:], channel)
    elif msg[0] == "도움말":
        if len(msg) == 1:
            post_message(token, channel, "도움말 관리 명령어는 '도움말 [구독/판매/구매/홈피팅/정산]'입니다.")
        else:
            handle_help(msg[1:], channel)
    elif msg[0] == "안녕":
        post_message(token, channel, "안녕하세요! 피키입니다. 명령어를 알고싶다면 '도움말'을 입력하세요 :)")
    else:
        handle_other_msg(msg, channel)

    return user_query


def event_handler(event_type, slack_event):
    channel = slack_event["event"]["channel"]
    string_slack_event = str(slack_event)
    if string_slack_event.find("{'type': 'user', 'user_id': ") != -1:  # 멘션으로 호출
        try:
            user_query = slack_event['event']['blocks'][0]['elements'][0]['elements'][1]['text']
            response = handle_msg(user_query, channel)

            return make_response("ok", 200, )
        except IndexError:
            pass

    message = "[%s] cannot find event handler" % event_type
    return make_response(message, 200, {"X-Slack-No-Retry": 1})


@app.route('/', methods=['POST'])
def hello_there():
    slack_event = json.loads(request.data)

    print(slack_event)

    if "challenge" in slack_event:
        return make_response(slack_event["challenge"], 200, {"content_type": "application/json"})
    if "event" in slack_event:
        event_type = slack_event["event"]["type"]
        return event_handler(event_type, slack_event)
    return make_response("There are no slack request events", 404, {"X-Slack-No-Retry": 1})


@app.route('/command', methods=['POST'])
def test():
    handle_msg(request.form['text'], request.form['channel_id'])
    return make_response("피키 커맨드 호출됨", 200, )


@app.route('/secret', methods=['POST'])
def secret():
    post_message(token, request.form['channel_id'], request.form['text'])
    return make_response("익명으로 메세지를 전달합니다.", 200, )


@app.route('/subscribe/add', methods=['POST'])
def subscribe_add():
    return subscribe("https://repick.seoul.kr/api/slack/subscribe/add", request.form['text'])


@app.route('/subscribe/deny', methods=['POST'])
def subscribe_deny():
    return subscribe("https://repick.seoul.kr/api/slack/subscribe/deny", request.form['text'])


def subscribe(request_url, query):
    requests.post(request_url,
                  headers={"Authorization": "Bearer " + token, "Content-Type": "application/json"},
                  json={
                      "orderNumber": query
                  })

    return make_response("구독 승인을 처리합니다: " + query + "\n구독 페이지에서 결과를 확인하세요.", 200, )


@app.route('/subscribe-list', methods=['POST'])
def subscribe_list():
    response = get_message_from_server("https://repick.seoul.kr/api/subscribe/admin/requested")

    res = "구독 요청 리스트입니다.\n\n"
    for each in response.json():
        res += handle_subscribe_response(each) + "\n"

    return res


def handle_subscribe_response(msg):
    # orderNumber, name, nickname, phoneNumber, subscribeType, lastModifiedDate 반환
    return "주문번호: " + msg['orderNumber'] + " 실명: " + msg['name'] + " 닉네임: " + msg['nickname'] + " 전화번호: " + msg['phoneNumber'] \
        + "\n 구독타입: " + msg['subscribeType'] + " 신청일: " + msg['lastModifiedDate']


@app.route('/order-update', methods=['POST'])
def order_update():
    request_url = "https://repick.seoul.kr/api/slack/order/update"
    query = request.form['text'].split()

    if query[1] == "입금완료":
        state = "PREPARING"
    elif query[1] == "배송중":
        state = "DELIVERING"
    elif query[1] == "배송완료":
        state = "DELIVERED"
    elif query[1] == "취소됨":
        state = "CANCELED"
    else:
        return make_response("상태는 '입금완료', '배송중', '배송완료', '취소됨' 중 하나여야 합니다.", 200, )

    requests.post(request_url,
                  headers={"Authorization": "Bearer " + token, "Content-Type": "application/json"},
                  json={
                      "orderNumber": query[0],
                      "sellState": state
                  })

    return make_response("주문 상태를 변경합니다: " + query[0] + " " + query[1] + "\n주문 페이지에서 결과를 확인하세요.", 200, )


@app.route('/order-list', methods=['POST'])
def order_list():
    request_url = "https://repick.seoul.kr/api/order/admin/state"
    query = request.form['text']

    if query == '미입금':
        state = "UNPAID"
    elif query == '입금완료':
        state = "PREPARING"
    elif query == '배송중':
        state = "DELIVERING"
    elif query == '배송됨':
        state = "DELIVERED"
    elif query == '취소됨':
        state = "CANCELED"

    response = get_message_from_server(request_url + "?orderState=" + state)

    res = "주문: " + query + " 리스트입니다.\n\n"
    for each in response.json():
        res += handle_order_response(each) + "\n"

    return res


def handle_order_response(msg):
    # orderNumber 반환
    return "주문번호: " + msg['orderNumber']


@app.route('/sell-order-update', methods=['POST'])
def sell_order_update():
    request_url = "https://repick.seoul.kr/api/slack/sell/update"
    query = request.form['text'].split()

    if query[1] == "요청됨":
        state = "REQUESTED"
    elif query[1] == "취소됨":
        state = "CANCELLED"
    elif query[1] == "배송됨":
        state = "DELIVERED"
    elif query[1] == "처리됨":
        state = "PUBLISHED"
    else:
        return make_response("상태는 '입금완료', '배송중', '배송완료', '취소됨' 중 하나여야 합니다.", 200, )

    requests.post(request_url,
                  headers={"Authorization": "Bearer " + token, "Content-Type": "application/json"},
                  json={
                    "orderNumber": query[0],
                    "sellState": state
                  })

    return make_response("판매 주문 상태를 변경합니다: " + query[0] + " " + query[1] + "\n옷장 수거 페이지에서 결과를 확인하세요.", 200, )


@app.route('/sell-order-list', methods=['POST'])
def sell_order_list():
    request_url = "https://repick.seoul.kr/api/sell/admin/"
    query = request.form['text']

    if query == '요청됨':
        state = "requested"
    elif query == '취소됨':
        state = "cancelled"
    elif query == '배송됨':
        state = "delivered"
    elif query == '처리됨':
        state = "published"

    response = get_message_from_server(request_url + state)

    res = "판매 주문: " + query + " 리스트입니다.\n\n"
    for each in response.json():
        res += handle_sell_order_response(each) + "\n"

    return res


def handle_sell_order_response(msg):
    return "주문번호: " + msg['orderNumber'] \
        + "\n 실명: " + msg['name'] \
        + "\n 전화번호: " + msg['phoneNumber'] \
        + "\n 신청일: " + msg['createdDate']\
        + "\n반환희망일: " + msg['returnDate'] \
        + "\n 수거주소: " + msg['address']['mainAddress'] + " " + msg['address']['detailAddress'] + " " + msg['address']['zipCode'] \
        + "\n 요청사항: " + msg['requestDetail'] \
        + "\n 수거옷장 수량: " + str(msg['productQuantity']) + "\n"


@app.route('/home-fitting-update', methods=['POST'])
def home_fitting_update():
    request_url = 'https://repick.seoul.kr/api/home-fitting/admin/'
    query = request.form['text'].split()
    request_url += query[0]

    if query[1] == '요청됨':
        request_url += "?homeFittingState=REQUESTED"
    if query[1] == '배송중':
        request_url += "?homeFittingState=DELIVERING"
    if query[1] == '배송됨':
        request_url += "?homeFittingState=DELIVERED"
    if query[1] == '반품신청됨':
        request_url += "?homeFittingState=RETURN_REQUESTED"
    if query[1] == '반품됨':
        request_url += "?homeFittingState=RETURNED"
    if query[1] == '구매됨':
        request_url += "?homeFittingState=PURCHASED"

    headers = {
        'accept': '*/*',
        "Authorization": "Bearer " + token,
        "Content-Type": "application/json",
    }

    requests.patch(request_url, headers=headers)

    res = "홈피팅 " + query[0] + "번의 상태를 " + query[1] + " 상태로 변경 완료했습니다.\n\n"

    return res


@app.route('/home-fitting-list', methods=['POST'])
def home_fitting_list():
    request_url = "https://repick.seoul.kr/api/home-fitting/admin"
    query = request.form['text']

    if query == '요청됨':
        request_url += "?homeFittingState=REQUESTED"
    if query == '배송중':
        request_url += "?homeFittingState=DELIVERING"
    if query == '배송됨':
        request_url += "?homeFittingState=DELIVERED"
    if query == '반품신청됨':
        request_url += "?homeFittingState=RETURN_REQUESTED"
    if query == '반품됨':
        request_url += "?homeFittingState=RETURNED"
    if query == '구매됨':
        request_url += "?homeFittingState=PURCHASED"

    response = get_message_from_server(request_url)

    res = "홈피팅 " + query + " 리스트입니다.\n\n"
    for each in response.json():
        res += handle_home_fitting_response(each) + "\n"

    return res


def handle_home_fitting_response(msg):
    # name, homeFittingId, lastModifiedDate를 반환
    return "홈피팅 번호: " + str(msg['homeFittingId'])\
        + " 실명: " + msg['product']['name']\
        + " 날짜: " + msg['lastModifiedDate']


@app.route('/settlement-update', methods=['POST'])
def settlement():
    request_url = "https://repick.seoul.kr/api/slack/settlement/update"
    query = request.form['text']

    requests.post(request_url,
                  headers={"Authorization": "Bearer " + token, "Content-Type": "application/json"},
                  json={
                      "productNumber": query
                  })

    return make_response("정산을 완료합니다: " + query + "\n정산 페이지에서 결과를 확인하세요.", 200, )


if __name__ == '__main__':
    app.run(debug=True, port=5002)
