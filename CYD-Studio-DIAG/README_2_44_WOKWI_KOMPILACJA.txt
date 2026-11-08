CYD Studio DIAG 2.44 – poprawka kompilacji w Wokwi i na ESP32

Błąd zgłoszony z PlatformIO (src/main.cpp:863):
  error: 'ww' was not declared in this scope
  cyd_style_caption(...,max(40,ww*42//100));
Przyczyna: Pythonowa operacja // emitowana do C++ i symbol ww z generatora zamiast liczby.
Naprawa: generator oblicza szerokość etykiety w Pythonie i wpisuje stałą liczbę pikseli.
Poprawione też wszystkie 7 zapisanych plików main.cpp z tym błędem.
Testy: generator 29/29. Kompilacja ESP32 i symulator Wokwi wykonywane u użytkownika przez TESTUJ_WOKWI.ps1.
Nie oznacza to, że zrzuty z Wokwi zostały wykonane.