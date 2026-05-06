"""TMC Query Node - Query mock TMC API for trains/flights/hotels"""

from typing import Dict, List
from datetime import date, datetime

from backend.schemas.state import TravelState, get_trip_field


def _parse_date(d) -> date:
    if isinstance(d, date):
        return d
    if isinstance(d, str):
        try:
            return datetime.strptime(d, "%Y-%m-%d").date()
        except ValueError:
            pass
    return datetime.now().date()


def tmc_query_node(state: TravelState) -> Dict:
    """Query TMC (mock) for available trains, flights, and hotels.

    Returns raw candidates for the recommender to rank.
    """
    trip = state.trip
    departure = get_trip_field(trip, "departure", "北京")
    destination = get_trip_field(trip, "destination", "上海")
    date_val = _parse_date(get_trip_field(trip, "date"))
    pax = get_trip_field(trip, "passengers", 1)
    date_str = date_val.strftime("%Y-%m-%d")

    candidates = []

    # --- Mock Train Data ---
    trains = [
        {
            "id": f"TRN-{date_str}-G1",
            "type": "train",
            "name": "G1 复兴号",
            "departure": departure,
            "destination": destination,
            "date": date_str,
            "departure_time": "06:00",
            "arrival_time": "10:28",
            "duration": "4h28m",
            "price": 553.0,
            "seat_class": "二等座",
            "available_seats": 120,
        },
        {
            "id": f"TRN-{date_str}-G3",
            "type": "train",
            "name": "G3 复兴号",
            "departure": departure,
            "destination": destination,
            "date": date_str,
            "departure_time": "07:00",
            "arrival_time": "11:28",
            "duration": "4h28m",
            "price": 553.0,
            "seat_class": "二等座",
            "available_seats": 85,
        },
        {
            "id": f"TRN-{date_str}-G5",
            "type": "train",
            "name": "G5 和谐号",
            "departure": departure,
            "destination": destination,
            "date": date_str,
            "departure_time": "08:00",
            "arrival_time": "12:45",
            "duration": "4h45m",
            "price": 553.0,
            "seat_class": "二等座",
            "available_seats": 200,
        },
        {
            "id": f"TRN-{date_str}-G7",
            "type": "train",
            "name": "G7 复兴号",
            "departure": departure,
            "destination": destination,
            "date": date_str,
            "departure_time": "09:00",
            "arrival_time": "13:48",
            "duration": "4h48m",
            "price": 553.0,
            "seat_class": "二等座",
            "available_seats": 150,
        },
        {
            "id": f"TRN-{date_str}-G9-1st",
            "type": "train",
            "name": "G9 一等座",
            "departure": departure,
            "destination": destination,
            "date": date_str,
            "departure_time": "10:00",
            "arrival_time": "14:28",
            "duration": "4h28m",
            "price": 933.0,
            "seat_class": "一等座",
            "available_seats": 40,
        },
        {
            "id": f"TRN-{date_str}-D713",
            "type": "train",
            "name": "D713 动卧",
            "departure": departure,
            "destination": destination,
            "date": date_str,
            "departure_time": "20:00",
            "arrival_time": "07:12",
            "duration": "11h12m",
            "price": 350.0,
            "seat_class": "动卧",
            "available_seats": 60,
        },
    ]
    candidates.extend(trains)

    # --- Mock Flight Data ---
    flights = [
        {
            "id": f"FLT-{date_str}-CA1321",
            "type": "flight",
            "name": "CA1321 国航",
            "departure": departure,
            "destination": destination,
            "date": date_str,
            "departure_time": "07:30",
            "arrival_time": "09:50",
            "duration": "2h20m",
            "price": 890.0,
            "cabin": "经济舱",
            "aircraft": "A320",
        },
        {
            "id": f"FLT-{date_str}-MU5123",
            "type": "flight",
            "name": "MU5123 东航",
            "departure": departure,
            "destination": destination,
            "date": date_str,
            "departure_time": "09:15",
            "arrival_time": "11:35",
            "duration": "2h20m",
            "price": 720.0,
            "cabin": "经济舱",
            "aircraft": "B737",
        },
        {
            "id": f"FLT-{date_str}-CZ6101",
            "type": "flight",
            "name": "CZ6101 南航",
            "departure": departure,
            "destination": destination,
            "date": date_str,
            "departure_time": "11:00",
            "arrival_time": "13:20",
            "duration": "2h20m",
            "price": 680.0,
            "cabin": "经济舱",
            "aircraft": "A321",
        },
        {
            "id": f"FLT-{date_str}-HU7601",
            "type": "flight",
            "name": "HU7601 海航",
            "departure": departure,
            "destination": destination,
            "date": date_str,
            "departure_time": "14:30",
            "arrival_time": "16:50",
            "duration": "2h20m",
            "price": 760.0,
            "cabin": "经济舱",
            "aircraft": "B787",
        },
        {
            "id": f"FLT-{date_str}-3U8801",
            "type": "flight",
            "name": "3U8801 川航",
            "departure": departure,
            "destination": destination,
            "date": date_str,
            "departure_time": "16:00",
            "arrival_time": "18:20",
            "duration": "2h20m",
            "price": 590.0,
            "cabin": "经济舱",
            "aircraft": "A319",
        },
        {
            "id": f"FLT-{date_str}-CA1321-biz",
            "type": "flight",
            "name": "CA1321 国航商务舱",
            "departure": departure,
            "destination": destination,
            "date": date_str,
            "departure_time": "07:30",
            "arrival_time": "09:50",
            "duration": "2h20m",
            "price": 2800.0,
            "cabin": "商务舱",
            "aircraft": "A320",
        },
    ]
    candidates.extend(flights)

    # --- Mock Hotel Data ---
    hotels = [
        {
            "id": f"HTL-{date_str}-001",
            "type": "hotel",
            "name": "上海中心商务酒店",
            "date": date_str,
            "price": 480.0,
            "price_per_night": 480.0,
            "rating": 4.5,
            "breakfast": True,
            "wifi": True,
            "distance_to_center": "0.5km",
            "address": "浦东新区陆家嘴环路",
        },
        {
            "id": f"HTL-{date_str}-002",
            "type": "hotel",
            "name": "快捷商务酒店",
            "date": date_str,
            "price": 280.0,
            "price_per_night": 280.0,
            "rating": 4.0,
            "breakfast": True,
            "wifi": True,
            "distance_to_center": "1.2km",
            "address": "静安区南京西路",
        },
        {
            "id": f"HTL-{date_str}-003",
            "type": "hotel",
            "name": "外滩精品酒店",
            "date": date_str,
            "price": 680.0,
            "price_per_night": 680.0,
            "rating": 4.8,
            "breakfast": True,
            "wifi": True,
            "distance_to_center": "0.2km",
            "address": "黄浦区外滩",
        },
        {
            "id": f"HTL-{date_str}-004",
            "type": "hotel",
            "name": "虹桥枢纽酒店",
            "date": date_str,
            "price": 350.0,
            "price_per_night": 350.0,
            "rating": 4.2,
            "breakfast": False,
            "wifi": True,
            "distance_to_center": "8km",
            "address": "闵行区虹桥枢纽",
        },
    ]
    candidates.extend(hotels)

    return {
        "current_step": "tmc_queried",
        "raw_candidates": candidates,
        "messages": [
            {
                "role": "assistant",
                "content": f"已查询到 {len(trains)} 趟高铁、{len(flights)} 个航班、{len(hotels)} 家酒店，正在为您智能推荐...",
            }
        ],
    }
