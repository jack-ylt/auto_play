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

    for s in sorted(config.sections()):
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

    for s in list(config.sections()):
        game = config.get(s, 'game')
        user = config.get(s, 'user')
        game_user_list.append((game, user))

    return game_user_list


def read_role_cfg(name='basic'):
    # 先加载基础配置，再更新特定配置
    # 这样，特定配置就不需要写那么多了
    basic_cfg = _read_role_cfg('basic')

    if name != 'basic':
        specific_cfg = _read_role_cfg(name)
        basic_cfg.update(specific_cfg)

    return basic_cfg
    

def _read_role_cfg(name):
    cfg_dict = {}

    config = configparser.RawConfigParser()
    config.read(f'./configs/roles_setting/{name}.cfg', encoding='utf-8')

    for sct in config.sections():
        if sct not in cfg_dict:
            cfg_dict[sct] = {}
            
        for opt in config[sct]:
            val = config.get(sct, opt).lower().strip()
            if val == 'yes':
                val = True
            elif val == 'no':
                val = False
            cfg_dict[sct][opt] = val

    return cfg_dict


if __name__ == '__main__':
    # print(read_account_cfg())
    print(read_role_cfg())