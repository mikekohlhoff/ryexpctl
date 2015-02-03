#include <windows.h>
#include <stdio.h>
#include <iostream.h>
#include "Dask.h"
U16 cardID;
I16 err;
F32 MySpecRate =5000000;//100000;
const U32 MaxSampleNum=10;

U16 DataArrayForOut[MaxSampleNum];
//U32 DataArrayForOut[MaxSampleNum];

void main()
{

	cardID=Register_Card(PCI_7300A_RevB, 0);

	cout<<"PCI-7300A Card ID = "<<cardID<<endl;
	//===========================================================================

	for(int k=0;k<MaxSampleNum;k++)
	{	
		if(k%2)
			DataArrayForOut[k]=0xFFFF;
		else 
			DataArrayForOut[k]=0x0000;
	}
	

	for(int j=0;j<1000;j++)
	{
	//===========================================================================
	
	//[software trigger]
	//err=DO_7300B_Config(cardID,16,TRIG_INT_PACER,P7300_WAIT_NO,P7300_TERM_OFF,P7300_DOREQ_POS,0);
	//err=DO_7300B_Config(cardID,16,TRIG_CLK_10MHZ,P7300_WAIT_NO,P7300_TERM_OFF,P7300_DOREQ_POS,0);
	//err=DO_7300B_Config(cardID,16,TRIG_CLK_20MHZ,P7300_WAIT_NO,P7300_TERM_OFF,P7300_DOREQ_POS,0);

	
	//[wait for trigger]
	//err=DO_7300B_Config(cardID,16,TRIG_INT_PACER,P7300_WAIT_TRG,P7300_TERM_OFF,P7300_DOREQ_POS,0);
	//err=DO_7300B_Config(cardID,16,TRIG_CLK_10MHZ,P7300_WAIT_TRG,P7300_TERM_OFF,P7300_DOREQ_POS,0);
	err=DO_7300B_Config(cardID,16,TRIG_CLK_20MHZ,P7300_WAIT_TRG,P7300_TERM_OFF,P7300_DOREQ_POS,0);
	


	if (err==0){cout<<"Digital Output Config Sucess !"<<endl;}else{cout<<"Digital Output Config Error !!"<<endl;}

	////////cout<<"Press any key to start"<<endl;getchar();

	BOOLEAN StopChkFlag;
	U32 AccessCnt=0;
	err=DO_ContWritePort(cardID,0,DataArrayForOut,MaxSampleNum,1,MySpecRate,ASYNCH_OP);
	
	do
	{
		err=DO_AsyncCheck(cardID,&StopChkFlag,&AccessCnt);
	}
	while(!StopChkFlag);

	err=DO_AsyncClear(cardID,&AccessCnt);
	if(err==0){cout<<"WorkDone!"<<endl;}else{cout<<"Error Crash !"<<endl;}
	cout<<"And Real Data send out number is "<<j<<AccessCnt<<endl;
	////Sleep(100);
	//===========================================================================
	}


	cout<<"Press any key to Release Das Card !!"<<endl;
	getchar();
	err=Release_Card(cardID);

}