#!/usr/bin/env python3
import pprint
import re
import sys

C_PLAIN = ['mp_order_items', 'mp_order_total']
C_SERIALIZED = ['Content', 'mp_cart_items']

GLOBAL_COUNT = {}

# Single purchased item
class Order:
    def __init__(self, name, price, quantity):
        self.name = name
        self.price = price
        self.quantity = quantity

    def __str__(self):
        return str(self.__dict__)

    def __repr__(self):
        return str(self.__dict__)

# Single customer merch order
class MerchOrder:
    def set_orders(self, orders):
        self.orders = orders

    def set_attrs(self, **content):
        self.__dict__.update(content)

    def to_csv(self):
        ret = []
        for k, v in self.__dict__.items():
            if k == 'orders':
                for o in v:
                    ret.append("{} ({}) ${}".format(o.name, o.quantity, o.price))
            else:
                ret.append(v)
        return ', '.join(ret)

# Retrieve last member in regex group
def getlast(group):
    for i in reversed(group):
        if len(i) > 0:
            if len(i.strip('"')) < 1:
                return ""
            else:
                return i.strip()

# Lazy PHP deserialize for mp_cart_items field
def lazyd_cart(data):
    orders = []
    groups = re.findall(r's:\d+:(\"\"([^\"]+)\"\"|\"\"\"\")|d:(\d+)|b:(\d+)|i:(\d+)', data)

    cur_name = None
    cur_price = None
    cur_quantity = None

    for i in range(0, len(groups) - 1, 2):
        if len(groups[i][0]) < 1:
            continue

        item = getlast(groups[i])
        value = getlast(groups[i + 1])

        if item.lower() == 'name':
            cur_name = value
        elif item.lower() == 'price':
            cur_price = value
        elif item.lower() == 'quantity':
            cur_quantity = value

        if cur_name and cur_price and cur_quantity:
            orders.append(Order(cur_name, cur_price, cur_quantity))
            if cur_name not in GLOBAL_COUNT:
                GLOBAL_COUNT[cur_name] = int(cur_quantity)
            else:
                GLOBAL_COUNT[cur_name] += int(cur_quantity)

            cur_name = None
            cur_price = None
            cur_quantity = None

    return orders

# Lazy PHP deserialize for Content field
def lazyd(data):
    ddict = {}

    groups = re.findall(r's:\d+:(\"\"([^\"]+)\"\"|\"\"\"\")|d:(\d+)|b:(\d+)|i:(\d+)', data)

    for i in range(0, len(groups) - 1, 2):
        if len(groups[i][0]) < 1:
            continue
        if getlast(groups[i]) in ['shipping_option', 'shipping_sub_option', 'special_instructions', 'company_name']:
            continue

        ddict[getlast(groups[i])] = getlast(groups[i + 1])

    return ddict

# Do it
def process_orders(wp_file):
    columns = []
    start = True
    orders = []

    with open(wp_file, 'r') as fin:
        for line in fin:
            if start:
                columns = line.split(',')
                start = False
                continue

            # Dennis is special
            line = line.replace(', ', ' ')
            fields = line.split(',')
            new_order = MerchOrder()

            for i in range(len(columns)):
                if columns[i] in C_PLAIN:
                    new_order.set_attrs(**{columns[i].lower(): fields[i]})
                elif columns[i] in C_SERIALIZED:
                    if columns[i] == 'Content':
                        new_order.set_attrs(**lazyd(fields[i]))
                    elif columns[i] == 'mp_cart_items':
                        new_order.set_orders(lazyd_cart(fields[i]))
            pprint.pprint(new_order.__dict__)
            orders.append(new_order)

    return orders


def main():
    if len(sys.argv) < 3:
        print("Usage: {} [wordpress.csv] [output.csv]".format(sys.argv[0]))
        exit(1)

    wp_file = sys.argv[1]
    output_file = sys.argv[2]

    orders = process_orders(wp_file)

    with open(output_file, 'w') as fout:
        for o in orders:
            fout.write("{}\n".format(o.to_csv()))
            
        fout.write("\nTotal Counts\n")
        sorted_by_value = sorted(GLOBAL_COUNT.items(), key=lambda x: x[0])
        for k,v in sorted_by_value:
            fout.write("{},{}\n".format(k,v))


if __name__ == '__main__':
    main()
    sys.exit()
