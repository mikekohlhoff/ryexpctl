#include "pcbtest.h"
#include <QApplication>

int main(int argc, char *argv[])
{
    QApplication a(argc, argv);
    PCBTest w;
    w.show();

    return a.exec();
}
