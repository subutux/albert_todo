# TODOs

This allows you to list, mark, edit (due dates), add todos on a caldav server.

Tested with the [radicale](https://github.com/Kozea/Radicale) server, but
should work with other caldav servers.

## Setup

1. Add the plugin folder to `~/.local/share/albert/org.albert.extension.python/modules/`
2. Activate the plugin in settings > extensions > python

At first lauch it will look for a configuration file. if not found, it will
create one for you and opens your editor with the file.

Basicly you define your iCal URLs in sections of the ini file. For example:

```ini
[Work]
url = https://my.calendar.host/work
username = myUsername
password = myPassword
```
**Note**: Don't add quotes around the values!

Save the file and trigger again with `t `. your todo's should show up!


## Triggers:

 * `t <query>`: lists the current todo's and filter with query
    * mark done
    * postpone for one hour
    * postpone 'till tomorrow
    * postpone 'till next week
    * reload the cache
 * `ta <query>`: Add a todo
    * No due date
    * Due 'till one hour
    * Due 'till tomorrow
    * Due 'till next week

## Due dates

this plugin tries to orden the todos by due date and places icons
when the due date is passed (❌) or due in 12 hours (⚠️).

Due dates that are passed are at the top, then those due in 12 hours,
then others.

