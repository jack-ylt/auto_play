import cursor
with cursor.HiddenCursor():     ## Cursor will stay hidden
    import time                 ## while code is being executed;
    for a in range(1,100):      ## afterwards it will show up again
        print(a)
        time.sleep(0.05)