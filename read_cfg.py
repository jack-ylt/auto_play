import configparser

# [1]
# game_name = mo_shi_jun_tun
# account = aa592729440
# passwd = Qq8738090
# server_ids = 4258, 4148, 20
def read_account_cfg():
    account_list = []

    config = configparser.RawConfigParser()
    config.read(r'./configs/account.cfg')

    for s in config.sections():
        account_dict = {}

        for opt in ['game_name', 'account', 'passwd']:
            account_dict[opt] = config.get(s, opt)

        opt = 'server_ids'
        if config.has_option(s, opt):
            numbers = config.get(s, opt)
            account_dict[opt] = [i.strip() for i in numbers.split(',') if i.strip()]
        else:
            account_dict[opt] = []

        account_list.append(account_dict)

    return account_list

if __name__ == '__main__':
    print(read_account_cfg())