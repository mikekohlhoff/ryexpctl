#ifndef PCBTEST_H
#define PCBTEST_H

#include <QWidget>

namespace Ui {
class PCBTest;
}

class PCBTest : public QWidget
{
    Q_OBJECT

public:
    explicit PCBTest(QWidget *parent = 0);
    ~PCBTest();

private:
    Ui::PCBTest *ui;
};

#endif // PCBTEST_H
