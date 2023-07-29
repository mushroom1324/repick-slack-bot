import json
import os
from flask import Flask, request, make_response
from slacker import Slacker
import requests


token = os.environ.get('TOKEN')
access_token = os.environ.get('ACCESS_TOKEN')

slack = Slacker(token)

app = Flask(__name__)


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
    if query[1] == "입금완료": state = "PREPARING"
    elif query[1] == "배송중": state = "DELIVERING"
    elif query[1] == "배송완료": state = "DELIVERED"
    elif query[1] == "취소됨": state = "CANCELED"
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
    if query[1] == "배달됨": state = "DELIVERED"
    elif query[1] == "취소됨": state = "CANCELED"
    elif query[1] == "처리됨": state = "PUBLISHED"
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

def handle_msg(user_query, channel):
    msg = user_query.split()
    if msg[0] == "구독":
        handle_subscribe(msg[1:], channel)
    elif msg[0] == "판매":
        handle_sell_order(msg[1:], channel)
    elif msg[0] == "구매":
        handle_order(msg[1:], channel)
    elif msg[0] == "홈피팅":
        handle_home_fitting(msg[1:], channel)
    elif msg[0] == "정산":
        handle_expense_settlement(msg[1:], channel)
    elif msg[0] == "도움말":
        if len(msg) > 1:
            handle_help(msg[1:], channel)
        else:
            post_message(token, channel, "도움말 관리 명령어는 '도움말 [구독/판매/구매/홈피팅/정산]'입니다.")
    elif msg[0] == "안녕":
        post_message(token, channel, "안녕하세요. 피키입니다. 명령어를 알고싶다면 '도움말'을 입력하세요!")
    else:
        post_message(token, channel, "잘못된 입력입니다. 명령어를 알고싶다면 '도움말'을 입력하세요.")
        return "잘못된 입력입니다."

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
    if "challenge" in slack_event:
        return make_response(slack_event["challenge"], 200, {"content_type": "application/json"})
    if "event" in slack_event:
        event_type = slack_event["event"]["type"]
        return event_handler(event_type, slack_event)
    return make_response("There are no slack request events", 404, {"X-Slack-No-Retry": 1})


if __name__ == '__main__':
    app.run(debug=True, port=5002)


