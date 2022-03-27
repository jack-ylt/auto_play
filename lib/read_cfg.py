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

    for s in sorted(config.sections(), reverse=True):
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


def read_role_cfg(name='default'):
    cfg_dict = {}
    config = configparser.RawConfigParser()
    config.read(f'./configs/roles_setting/{name}.cfg')

    for sct in sorted(config.sections(), reverse=True):
        cfg_dict[sct] = {}
        for opt in config[sct]:
            cfg_dict[sct][opt] = config.get(sct, opt)

    return cfg_dict


if __name__ == '__main__':
    # print(read_account_cfg())
    print(read_role_cfg())