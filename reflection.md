# Reflection: Profile Comparisons

---

## 1. High-Energy Pop vs. Chill Lofi

These two profiles are opposites, and the results show exactly that. The High-Energy Pop user wants fast, loud, driving music — and gets Gym Hero and Sunrise City at the top, both pop songs with energy close to 0.9. The Chill Lofi user wants something calm and quiet — and gets Midnight Coding and Library Rain, both slow lofi tracks sitting around energy 0.4. Neither list overlaps at all, which makes sense. When preferences are clear and the catalog actually has songs for them, the system works the way you'd hope. These two profiles are the "easy cases" — the scoring logic was basically designed around profiles like these.

---

## 2. High-Energy Pop vs. Sad But Pumped

Both profiles want the same energy level (0.9), but the outputs look nothing alike. The High-Energy Pop user gets Gym Hero and Sunrise City — fast, upbeat pop songs. The Sad But Pumped user gets Midnight Gospel by Blue Crane — a slow, mournful blues track with energy 0.38, almost half of what was asked for.

Why does this happen? Because the scoring system gives extra points for matching genre and mood, and those bonuses are big enough to pull the "wrong" song to the top. Midnight Gospel is the only blues song with a sad mood in the catalog, so it earns the maximum genre and mood bonus. That bonus outweighs the fact that its energy is way off. The system is essentially saying: "I know you asked for something fast, but this song ticks two other boxes so it wins." 

This is the core tension in the design — when a user's preferences conflict with each other, the system doesn't notice the conflict. It just adds up the points and returns whatever scored highest.

---

## 3. Deep Intense Rock vs. Intense Lofi Coder

These two profiles ask for almost the same thing — intense mood, high energy — but in different genres. The rock user gets Storm Runner (#1, rock, intense, energy 0.91): a near-perfect match on all three dimensions. The lofi user gets Midnight Coding (#1, lofi, chill, energy 0.42): a song that matches genre but is calm and low-energy — basically the opposite of what was asked.

This is the clearest demonstration of the genre filter bubble in these experiments. The lofi label is powerful enough on its own to push three chill lofi songs to the top, blocking out songs that actually match the mood and energy the user wanted. The rock user happened to get lucky because the catalog has one rock song that is also intense and high-energy. The lofi user has no such luck — no lofi song in the catalog is intense. The system doesn't know that. It just gives genre points to every lofi song and moves on.

After we halved the genre weight, Storm Runner jumped to #1 for the Intense Lofi Coder profile — meaning the fix worked, but only because we manually adjusted a number. A real user would have no way to do that themselves.

---

## 4. Chill Lofi vs. Intense Lofi Coder

Both users prefer lofi. But the Chill Lofi user wants calm, low-energy music, and the Intense Lofi Coder wants high-energy, intense music. The Chill Lofi user gets exactly what they asked for: the top three results are all lofi songs with matching mood and energy. The Intense Lofi Coder gets the same three lofi songs — just in a slightly different order — because genre points dominate either way.

In other words, two very different people get nearly the same playlist. One of them is happy about it. The other asked for something completely different and has no idea the system didn't understand their request. This is what a filter bubble looks like in practice: the system confidently returns results, but it's really just re-surfacing the same small pool of songs regardless of what the user actually wanted.

---

## 5. Opera Buff vs. Genre Rules All

Both profiles expose problems with how genre is handled, but in opposite directions.

The Opera Buff asked for a genre that doesn't exist in the catalog. With no songs to match on genre, the entire genre bonus just disappears — the score ceiling drops from 4.0 to 2.0 for every song. The system falls back to mood and energy, and Golden Hour rises to the top because it perfectly matches both. This actually works out okay, but only by accident: the user asked for opera and got soul. The system gave no warning that it couldn't find anything in their genre.

The Genre Rules All profile has the opposite problem — the genre exists (ambient), but there is only one ambient song in the catalog, and it is calm and quiet (energy 0.28). The user wanted energetic, high-energy music (0.95). Before the weight shift, that single ambient song won anyway because the genre bonus alone was enough. After the weight shift, the energetic EDM song took the top spot. This pair together shows that genre being missing is actually safer than genre being present but wrong — at least when the genre doesn't exist, the system is forced to look at other signals.

---

## 6. Absolute Silence vs. Chill Lofi

Both users want quiet, low-energy music. The Chill Lofi user gets a list full of matching lofi tracks and the results feel right. The Absolute Silence user asks for the absolute minimum energy (0.0) and gets Rainy Window, a classical piano piece — which is reasonable — but the rest of the list is just "whatever happens to be the least energetic in the catalog," with no connection to classical or melancholy.

The interesting finding here is about limits. The lowest energy song in the catalog is Rainy Window at 0.22 — there is no song with energy 0.0 or even close to it. So the system can never give the Absolute Silence user a full energy score. That point is always slightly out of reach. This matters because it means users with extreme preferences will always get a weaker match than users whose preferences sit in the middle of the catalog's range. The system is quietly biased toward users whose taste matches where most of the songs happen to cluster.

---

## Why Does Gym Hero Keep Showing Up?

Gym Hero is a pop song with energy 0.93. That makes it one of the closest songs in the catalog to a high energy target like 0.9. In a 20-song catalog, there are only four songs with energy above 0.9 — and Gym Hero is one of them.

Imagine a shelf of twenty books, and someone asks for "something exciting." Four of those books have a big red "exciting" sticker on the spine. No matter who walks in asking for something exciting — whether they want a thriller, a sports story, or a horror novel — the librarian keeps pointing to those four books because they are the only ones tagged "exciting." Gym Hero is one of those four books.

The problem is not that Gym Hero is a bad recommendation for a High-Energy Pop fan. It is a fine recommendation there. The problem is that it shows up for almost every profile that lacks a genre match, because energy is the only signal left when genre and mood don't fire — and Gym Hero's energy number is hard to beat. A real recommender would have hundreds of songs at every energy level, so no single song could dominate this way. With only 20 songs, a handful of tracks end up representing entire regions of the preference space, and every user whose taste falls in that region gets the same small handful of results.
