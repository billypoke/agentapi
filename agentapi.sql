CREATE TABLE pilots(id INTEGER primary key, email text, name text, keyid integer, vcode text, active_account integer default 0, in_alliance integer default 0, slack_active integer default 0, discordid text);
CREATE TABLE recruits(id INTEGER primary key, name text, keyid integer, vcode text, blob text, status integer default 0, sb integer default 0, astero integer default 0, strat integer default 0, recon integer default 0, blops integer default 0, t3 integer default 0, lastagent text, dateadded text, datelasttouch text)
