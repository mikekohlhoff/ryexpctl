#include "pcbtest.h"
#include "ui_pcbtest.h"

PCBTest::PCBTest(QWidget *parent) :
    QWidget(parent),
    ui(new Ui::PCBTest)
{
    ui->setupUi(this);
}

PCBTest::~PCBTest()
{
    delete ui;
}
