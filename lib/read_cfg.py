import configparser

# [1]
# game = mo_shi_jun_tun
# user = aa592729440
# passwd = Qq8738090
# server_ids = 4258, 4148, 20
def read_account_cfg():
    account_list = []

    config = configparser.RawConfigParser()
    config.read(r'./configs/account.cfg', encoding='utf-8')

    for s in sorted(config.sections(), reverse=True):
        account_dict = {}

        for opt in ['game', 'user', 'passwd']:
            account_dict[opt] = config.get(s, opt)

        opt = 'server_ids'
        if config.has_option(s, opt):
            numbers = config.get(s, opt)
            account_dict[opt] = [i.strip() for i in numbers.split(',') if i.strip()]
        else:
            account_dict[opt] = []

        account_list.append(account_dict)

    return account_list

def read_game_user():
    game_user_list = []

    config = configparser.RawConfigParser()
    config.read(r'./configs/account.cfg', encoding='utf-8')

    for s in sorted(config.sections(), reverse=True):
        game = config.get(s, 'game')
        user = config.get(s, 'user')
        game_user_list.append((game, user))

    return game_user_list


def read_role_cfg(name='basic'):
    cfg_dict = {}
    config = configparser.RawConfigParser()
    config.read(f'./configs/roles_setting/{name}.cfg', encoding='utf-8')

    for sct in sorted(config.sections(), reverse=True):
        cfg_dict[sct] = {}
        for opt in config[sct]:
            cfg_dict[sct][opt] = config.get(sct, opt)

    return cfg_dict


if __name__ == '__main__':
    # print(read_account_cfg())
    print(read_role_cfg())