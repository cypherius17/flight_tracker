import pandas as pd
import time
from datetime import date
import argparse

import smtplib
import ssl
from selenium import webdriver
from selenium.webdriver.support.ui import WebDriverWait

VIETJET_URL = "https://www.vietjetair.com/Sites/Web/vi-VN/Home"
RETURN_TICKET = '//input[@id="ctl00_UcRightV31_RbRoundTrip"]'
ONE_WAY_TICKET = '//input[@id="ctl00_UcRightV31_RbOneWay"]'
DEPARTURE_PICKER_ID = "select2-selectOrigin-container"
LOCATION_INPUT = "select2-search__field"
ARRIVAL_PICKER_ID = "select2-selectDestination-container"
DEPARTURE_DATE_INPUT_ID = "ctl00_UcRightV31_TxtDepartDate"
ARRIVAL_DATE_INPUT_ID = "ctl00_UcRightV31_TxtReturnDate"
NEXT_MONTH_BUTTON_ID = "ui-datepicker-next"
SUBMIT_BUTTON_NAME = "ctl00$UcRightV31$BtSearch"
DAY_PICKER_CLASS_NAME = "ui-state-default"

SENDER = "<SENDER_EMAIL_ADDRESS>"
PASSWORD = "<SENDER_EMAIL_APP_PASSWORD>"
RECEIVER = "<RECEIVER_EMAIL_ADDRESS>"

MESSAGE = """
    Flight that matches your requirement has been found!\n
    Total fee: {} VND\n
    BOOK IT RIGHT AWAY!!!
    """

driver = webdriver.Chrome(executable_path='chromedriver')
driver.get(VIETJET_URL)

wait = WebDriverWait(driver, 10)


def get_month_diff(start_date, end_date):
    month_diff = (end_date.year - start_date.year) * 12  + end_date.month - start_date.month
    return month_diff


class FlightScanner(object):
    def __init__(self, origin, arrival, one_way, departing, returning):
        self.origin = origin
        self.arrival = arrival
        self.one_way = one_way
        self.departing = departing
        self.returning = returning

    def pick_ticket(self):
        ticket = ONE_WAY_TICKET if self.one_way else RETURN_TICKET
        ticket_type = driver.find_element_by_xpath(ticket)
        ticket_type.click()


def input_location(location_id, location_input, location_name):
    location_picker = driver.find_element_by_id(location_id)
    location_picker.click()
    time.sleep(1)

    location_input = driver.find_element_by_class_name(location_input)
    location_input.clear()
    location_input.send_keys(location_name)
    time.sleep(0.5)
    first_item = driver.find_element_by_xpath(
        "//*[contains(@id, '{}')]".format(location_name)
    )
    first_item.click()


def input_date(date_input_id, start, end):
    day, month, year = end.day, end.month, end.year
    date_picker = driver.find_element_by_id(date_input_id)
    time.sleep(1)
    date_picker.click()
    month_diff = get_month_diff(start, end)
    while month_diff > 0:
        next_month_button = driver.find_element_by_class_name(
            NEXT_MONTH_BUTTON_ID
        )
        month_diff -= 1
        next_month_button.click()
    day_pickers = driver.find_elements_by_class_name(DAY_PICKER_CLASS_NAME)
    day_pickers[day-1].click()


def get_cheapest_ticket(ticket_list_id):
    dep_tickets = driver.find_element_by_id(ticket_list_id)
    promos = dep_tickets.find_elements_by_xpath(
        "//*[contains(@id, 'Promo-O')]"
    )
    ecos = dep_tickets.find_elements_by_xpath(
        "//*[contains(@id, 'Eco-O')]"
    )
    cheapest_promo = min([int(promo.text.split()[0].replace(',', '')) for promo in promos])
    cheapest_eco = min([int(eco.text.split()[0].replace(',', '')) for eco in ecos])
    cheapest_ticket = cheapest_promo if cheapest_promo else cheapest_eco
    return cheapest_ticket


def scan_flights(origin, arrival, one_way, departing, returning):
    pick_ticket()
    input_location(DEPARTURE_PICKER_ID, LOCATION_INPUT, origin)
    input_location(ARRIVAL_PICKER_ID, LOCATION_INPUT, arrival)
    input_date(DEPARTURE_DATE_INPUT_ID, date.today(), departing)
    input_date(ARRIVAL_DATE_INPUT_ID, departing, returning)
    submit_button = driver.find_element_by_name(SUBMIT_BUTTON_NAME)
    submit_button.click()
    time.sleep(10)
    cheapest_dep = get_cheapest_ticket("toDepDiv")
    cheapest_return = get_cheapest_ticket("toRetDiv")
    return cheapest_dep + cheapest_return


class EmailNotifier(object):
    def __init__(self, receiver, result):
        self.sender = SENDER
        self.password = PASSWORD
        self.receiver = receiver
        self.result = result
        self.port = 587
        self.smtp_server = "smtp.gmail.com"
        self.message = MESSAGE.format(result)

    def notify(self):
        context = ssl.create_default_context()
        with smtplib.SMTP(self.smtp_server, self.port) as server:
            server.ehlo()
            server.starttls(context=context)
            server.ehlo()
            server.login(self.sender, self.password)
            server.sendmail(self.sender, self.receiver, self.message)


def main(origin, arrival, one_way, departing, returning, price):
    flight_scanner = FlightScanner(origin, arrival, one_way, departing, returning)
    result = flight_scanner.scan_flights()
    if result <= price:
        email_notifier = EmailNotifier(RECEIVER, result)
        email_notifier.notify()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--origin", "-o",
        help="IATA code of origin airport, e.g HAN for Hanoi",
        required=True
    )
    parser.add_argument(
        "--arrival", "-a",
        help="IATA code of destination airport, e.g SGN for Ho Chi Minh City",
        required=True
    )
    parser.add_argument(
        "--one_way", "-ow",
        help="Is this one-way booking",
        required=True
    )
    parser.add_argument(
        "--departing", "-d",
        help="Day of departure dd/mm/yyyy",
        required=True
    )
    parser.add_argument(
        "--returning", "-r",
        help="Day of return dd/mm/yyyy",
        required=True
    )
    parser.add_argument(
        "--price", "-p",
        help="Expected price",
        required=True
    )
    args = parser.parse_args()

    departing = args.departing.split('/')
    departing = date(
        int(departing[-1]),
        int(departing[-2]),
        int(departing[-3])
    )

    returning = args.returning.split('/')
    returning = date(
        int(returning[-1]),
        int(returning[-2]),
        int(returning[-3])
    )

    main(
        args.origin,
        args.arrival,
        args.one_way,
        departing,
        returning,
        int(args.price)
    )

