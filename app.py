import hashlib
import hmac
import time
import json
import os
from flask import Flask, request, make_response, abort
from slacker import Slacker
import requests

token = os.environ.get('TOKEN')
access_token = os.environ.get('ACCESS_TOKEN')
SIGNING_SECRET = os.environ.get('SLACK_SIGNING_SECRET')

slack = Slacker(token)

app = Flask(__name__)


@app.before_request
def before_request():
    # Check only for routes that require Slack verification
    if not verify_slack_request(request):
        abort(403)


def verify_slack_request(request):
    # 1. Get Slack request headers
    slack_signature = request.headers.get('X-Slack-Signature', '')
    slack_request_timestamp = request.headers.get('X-Slack-Request-Timestamp', '')

    # 2. Check timestamp
    if abs(time.time() - float(slack_request_timestamp)) > 60 * 5:
        # The request timestamp is older than five minutes
        return False

    # 3. Create a string based on the request
    basestring = f"v0:{slack_request_timestamp}:".encode('utf-8') + request.get_data()

    # 4. Generate a signature using HMAC SHA256
    my_signature = 'v0=' + hmac.new(
        SIGNING_SECRET.encode('utf-8'),
        basestring,
        hashlib.sha256
    ).hexdigest()

    # 5. Compare the generated signature with Slack's signature
    if hmac.compare_digest(my_signature, slack_signature):
        return True

    return False


def get_message_from_server(url):
    headers = {
        "Authorization": "Bearer " + access_token,
        "Content-Type": "application/json",
    }

    return requests.get(url, headers=headers)


def post_message(token, channel, text):
    response = requests.post("https://slack.com/api/chat.postMessage",
                             headers={"Authorization": "Bearer " + token},
                             data={"channel": channel, "text": text})
    print(response)


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
                  headers={"Authorization": "Bearer " + access_token, "Content-Type": "application/json"},
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
                  headers={"Authorization": "Bearer " + access_token, "Content-Type": "application/json"},
                  json={
                      "orderNumber": query[0],
                      "sellState": state
                  })


def handle_expense_settlement(query, channel):
    request_url = "https://repick.seoul.kr/api/slack/settlement/update"

    if len(query) > 1:
        post_message(token, channel, "잘못된 입력입니다. 정산 관리 양식은 '정산 [상품번호]입니다.")
        return "잘못된 입력입니다."

    requests.post(request_url,
                  headers={"Authorization": "Bearer " + access_token, "Content-Type": "application/json"},
                  json={
                      "productNumber": query[0],
                  })


def handle_help(query, channel):
    if query[0] == "판매":
        post_message(token, channel, "판매 관리 명령어는 '판매 [주문번호] [배달됨/취소됨/처리됨]'입니다.")
    if query[0] == "구매":
        post_message(token, channel, "구매 관리 명령어는 '구매 [주문번호] [입금완료/배송중/배송완료/취소됨]'입니다.")
    if query[0] == "정산":
        post_message(token, channel, "정산 관리 명령어는 '정산 [상품번호]'입니다.")
    else:
        post_message(token, channel, "도움말 관리 명령어는 '도움말 [구독/판매/구매/홈피팅/정산]'입니다.")


def handle_other_msg(query, channel):
    if query[0] == "테스트":
        post_message(token, channel, "피키 v2.0")
    elif query[0] == "피키":
        post_message(token, channel, "피키는 제 이름이에요. 저는 리픽 서비스를 위해 일한답니다.")
    else:
        post_message(token, channel, "잘못된 입력입니다. 명령어를 알고싶다면 '도움말'을 입력하세요.")
        return "잘못된 입력입니다."


def handle_msg(user_query, channel):
    msg = user_query.split()
    if msg[0] == "판매":
        if len(msg) == 1:
            post_message(token, channel, "판매 관리 명령어는 '판매 [주문번호] [배달됨/취소됨/처리됨]'입니다.")
        else:
            handle_sell_order(msg[1:], channel)
    elif msg[0] == "구매":
        if len(msg) == 1:
            post_message(token, channel, "구매 관리 명령어는 '구매 [주문번호] [입금완료/배송중/배송완료/취소됨]'입니다.")
        else:
            handle_order(msg[1:], channel)
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
                  headers={"Authorization": "Bearer " + access_token, "Content-Type": "application/json"},
                  json={
                      "orderNumber": query[0],
                      "orderState": state
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
    return "주문번호: " + msg['order']['orderNumber'] + " 실명: " + msg['order']['personName'] + " 전화번호: " + msg['order']['phoneNumber'] \
        + "\n 주소: " + msg['order']['address']['mainAddress'] + " " + msg['order']['address']['detailAddress'] + " " + msg['order']['address']['zipCode'] \
        + "\n 주문일: " + msg['order']['lastModifiedDate'] + "\n"


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
                  headers={"Authorization": "Bearer " + access_token, "Content-Type": "application/json"},
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
    return "주문번호: " + str(msg['orderNumber']) \
        + "\n 실명: " + str(msg['name']) \
        + "\n 전화번호: " + str(msg['phoneNumber']) \
        + "\n 신청일: " + str(msg['createdDate']) \
        + "\n반환희망일: " + str(msg['returnDate']) \
        + "\n 수거주소: " + str(msg['address']['mainAddress']) + " " + str(msg['address']['detailAddress']) + " " + str(msg['address']['zipCode']) \
        + "\n 요청사항: " + str(msg['requestDetail']) \
        + "\n 수거옷장 수량: " + str(msg['productQuantity']) + "\n"


@app.route('/settlement-update', methods=['POST'])
def settlement():
    request_url = "https://repick.seoul.kr/api/slack/settlement/update"
    query = request.form['text']

    requests.post(request_url,
                  headers={"Authorization": "Bearer " + access_token, "Content-Type": "application/json"},
                  json={
                      "productNumber": query
                  })

    return make_response("정산을 완료합니다: " + query + "\n정산 페이지에서 결과를 확인하세요.", 200, )


if __name__ == '__main__':
    app.run(debug=True, port=5002)
