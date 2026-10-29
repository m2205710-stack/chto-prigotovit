/* Запускатор для Windows: стартует встроенный Python (папка runtime)
 * с программой из папки app, чтобы пользователю не нужно было ставить Python.
 *
 * Сборка (MinGW):  x86_64-w64-mingw32-gcc -municode -O2 launcher.c res.o -o "Что приготовить.exe" -mwindows
 * С флагом -DCONSOLE_SCRIPT=L"tests\\test_tz.py" собирается консольный запуск проверок ТЗ.
 */
#include <windows.h>
#include <wchar.h>

#if defined(GUI_SCRIPT)
#define PYTHON L"pythonw.exe"
#define SCRIPT GUI_SCRIPT
#elif !defined(CONSOLE_SCRIPT)
#define PYTHON L"pythonw.exe"
#define SCRIPT L"main.py"
#else
#define PYTHON L"python.exe"
#define SCRIPT CONSOLE_SCRIPT
#endif

static void fail(const wchar_t *what)
{
    wchar_t msg[1200];
    swprintf(msg, 1200,
             L"Не удалось запустить приложение: %ls\n\n"
             L"Проверьте, что папки «app» и «runtime» лежат рядом с этим файлом. "
             L"Если архив не распакован, сначала распакуйте его целиком.", what);
    MessageBoxW(NULL, msg, L"Что приготовить?", MB_ICONERROR | MB_OK);
}

#ifndef CONSOLE_SCRIPT
int WINAPI wWinMain(HINSTANCE h, HINSTANCE p, PWSTR cmd, int show)
#else
int wmain(void)
#endif
{
    wchar_t dir[MAX_PATH], py[MAX_PATH], script[MAX_PATH], line[3 * MAX_PATH];
    DWORD n = GetModuleFileNameW(NULL, dir, MAX_PATH);
    if (n == 0 || n >= MAX_PATH) { fail(L"слишком длинный путь к папке"); return 1; }
    wchar_t *slash = wcsrchr(dir, L'\\');
    if (slash) *slash = 0;

    swprintf(py, MAX_PATH, L"%ls\\runtime\\%ls", dir, PYTHON);
    swprintf(script, MAX_PATH, L"%ls\\app\\%ls", dir, SCRIPT);
    if (GetFileAttributesW(py) == INVALID_FILE_ATTRIBUTES) { fail(L"не найден встроенный Python"); return 1; }
    if (GetFileAttributesW(script) == INVALID_FILE_ATTRIBUTES) { fail(L"не найдена программа"); return 1; }

    /* библиотеки Python и Qt ищутся в папках runtime */
    static wchar_t path[32767];
    wchar_t old[30000];
    DWORD m = GetEnvironmentVariableW(L"PATH", old, 30000);
    if (m == 0 || m >= 30000) old[0] = 0;
    swprintf(path, 32767, L"%ls\\runtime;%ls\\runtime\\Library\\bin;%ls\\runtime\\DLLs;%ls", dir, dir, dir, old);
    SetEnvironmentVariableW(L"PATH", path);
    SetEnvironmentVariableW(L"PYTHONHOME", NULL);
    SetEnvironmentVariableW(L"PYTHONPATH", NULL);
    SetEnvironmentVariableW(L"PYTHONDONTWRITEBYTECODE", L"1");
    SetEnvironmentVariableW(L"PYTHONIOENCODING", L"utf-8");

    swprintf(line, 3 * MAX_PATH, L"\"%ls\" \"%ls\"", py, script);
    STARTUPINFOW si = {0};
    PROCESS_INFORMATION pi = {0};
    si.cb = sizeof(si);
#ifndef CONSOLE_SCRIPT
    if (!CreateProcessW(py, line, NULL, NULL, FALSE, 0, NULL, dir, &si, &pi)) {
        fail(L"Windows не разрешил запуск");
        return 1;
    }
#else
    if (!CreateProcessW(py, line, NULL, NULL, FALSE, 0, NULL, dir, &si, &pi)) {
        fail(L"Windows не разрешил запуск");
        return 1;
    }
    WaitForSingleObject(pi.hProcess, INFINITE);
    {   /* окно не закрывается сразу, чтобы можно было прочитать результат */
        HANDLE out = GetStdHandle(STD_OUTPUT_HANDLE), in = GetStdHandle(STD_INPUT_HANDLE);
        const wchar_t *msg = L"\r\nНажмите Enter, чтобы закрыть окно...";
        DWORD w;
        WriteConsoleW(out, msg, (DWORD)wcslen(msg), &w, NULL);
        wchar_t buf[8];
        ReadConsoleW(in, buf, 1, &w, NULL);
    }
#endif
    CloseHandle(pi.hThread);
    CloseHandle(pi.hProcess);
    return 0;
}
