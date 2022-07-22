# Dynamic Playlist Predicate  (DPP)
## _Integrating Calendarific & Screenly- What could be better?_

Screenly is one of the most popular digital signage solutions on the web. 

Calendarific is a developer-friendly, worldwide RESTful API giving you access to public, local & bank holidays and observances; and spanning over 230 countries, 3,300+ states and 100+ languages.

## What does this do?
Imagine having to update the predicate (run config) for a playlist each and every year? Many playlists, many configs, no time! Introducing DPP. DPP takes the pain AWAY from manual updates to the time specific predicate. Simply name your playlist [according to the holiday](https://calendarific.com/holidays/2022/US) (or range) and run! It's THAT simple!

## How do I use it? Simply name & run!
- Set environment variables for API Keys :)
- Name a playlist according to a holiday (i.e. Independance Day)
- Name a playlist for a range including two holidays (i.e. Summer|Memorial Day|Labor Day|RANGE)
- Run!

## Range examples
- {Title}|{Start Holiday}|{End Holiday}
- Summer|Memorial Day|Labor Day
- Before Christmas|90|Christmas Day (results in 90 days before Christmas Day)
- After Christmas|Christmas Day|90 (results in 90 days after Christmas Day)
- Random|Memorial Day+8|Christmas Day+1 (results in 8 days after Memorial Day and 1 day after Christmas Day)
- Week Before and After Christmas|7|Christmas Day+7 (week before and after Christmas Day)

## License

**Free Software, Hell Yeah!**
