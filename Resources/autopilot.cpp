#include <string>

int main(int argc, const char* argv[]) {
    std::string command = "python3 ~/Library/com.UmActually.Autopilot/main.py";
    for (int i = 1; i < argc; ++i) {
        command += " ";
        command += argv[i];
    }
    system(command.c_str());
    return 0;
}
