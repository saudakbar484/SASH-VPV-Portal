#include <stdint.h>
#include <stdio.h>
#include <time.h>

#if defined(__linux__)
#include <unistd.h>
#include <sys/time.h>
#else
#include <Windows.h>
#define usleep(a)	(Sleep(a/1000))
#endif

#include <string.h>

#include <xr_vein_api.h>



void showTip(int32_t cap_tip)
{
    switch (cap_tip) {
        case PV_TIP_INPUT_PALM: printf("请放入手掌\n"); return;
        case PV_TIP_MOVE_FARAWAY: printf("请将手掌远离一些\n"); return;
        case PV_TIP_MOVE_CLOSER: printf("请将手掌靠近一些\n"); return;
        case PV_TIP_INVALID_BRIGHT: printf("亮度异常\n"); return;
        case PV_TIP_KEEP_PALM_STABLE: printf("请保持手掌姿势稳定\n"); return;
        case PV_TIP_KEEP_PALM_DIRECTION: printf("请保持正确的手掌朝向\n"); return;
        case PV_TIP_MOVE_PALM_DOWN: printf("请将手掌靠下一些\n"); return;
        case PV_TIP_MOVE_PALM_UP: printf("请将手掌靠上一些\n"); return;
        case PV_TIP_MOVE_PALM_LEFT: printf("请将手掌靠左一些\n"); return;
        case PV_TIP_MOVE_PALM_RIGHT: printf("请将手掌靠右一些\n"); return;
        case PV_TIP_CAP_SUCCESS: printf("采集成功\n"); return;
        case PV_TIP_ENROLL_FINISH: printf("注册成功\n"); return;
        default: return;
    }
}

bool EnrollProcess(void *alg_handle, uint8_t *feat_buf)
{
    if(alg_handle == NULL)
        return false;


    int32_t ret = XR_Vein_StartEnrollPalm(alg_handle);
    if(ret != PV_OK)
    {
        printf("Init enroll env failed: %d\n", ret);
        return false;
    }
    printf("XR_Vein_InitEnrollEnv\n");


    int32_t try_idx = 0;
    int32_t cap_tip = 0;
    int32_t enroll_state = 0;
    sPalmInfo palm_info;
    while(try_idx < 100)
    {
        uint8_t high_bright = 0;
        ret = XR_Vein_GetEnrollState(alg_handle, &enroll_state, &cap_tip);
        if(ret == PV_OK)
        {
            if(enroll_state == 100 || enroll_state == 101)
            {
                break;
            }
            else
            {
                showTip(cap_tip);
            }
        }
        else
        {
            break;
        }
        usleep(50*1000);
        try_idx++;
    }

    if(enroll_state != 100)
    {
        printf("注册失败\n");
        return false;
    }

    int32_t img_buf_len = 640 * 480;
    uint8_t *img_buf = new uint8_t[img_buf_len];


    delete[] img_buf;

    int32_t feat_len = XR_PALM_FEATURE_SIZE;

    ret = XR_Vein_FinishEnroll(alg_handle, img_buf, &img_buf_len, feat_buf, &feat_len);
    if(ret != PV_OK)
    {
        printf("export feature failed: %d\n", ret);
        delete[] img_buf;
        return false;
    }

    FILE *fp = fopen("reg_img.bin", "wb");
    fwrite(img_buf, 1, img_buf_len, fp);
    fclose(fp);

    printf("注册成功\n");
    delete[] img_buf;
    return true;
}


bool RecgProcess(void *alg_handle, uint8_t *reg_feat_buf)
{
    if(alg_handle == NULL)
        return false;

    uint8_t *recg_feat_buf = new uint8_t[XR_PALM_FEATURE_SIZE];
    int32_t try_idx = 0;
    int32_t cap_tip = 0;
    while(try_idx < 100)
    {
        sPalmInfo palm_info;
        uint8_t high_bright = 0;

        int32_t roi_buf_len = 112 * 112;
        //detect hand test

#if defined(__linux__)
        struct timeval start_tick, end_tick;
        gettimeofday(&start_tick, NULL);
#endif

        int32_t liveness_flag = 0;

        high_bright = 0;
        int32_t feat_len = XR_PALM_FEATURE_SIZE;
        int32_t ret = XR_Vein_CapRecgFeat(alg_handle, recg_feat_buf, &feat_len, &cap_tip);
#if defined(__linux__)
        gettimeofday(&end_tick, NULL);
        int32_t ms = (end_tick.tv_sec - start_tick.tv_sec)*1000 + (end_tick.tv_usec - start_tick.tv_usec) / 1000;
        printf("Full Grab feat time: %dms, high bright: %d\n", ms, high_bright);
#endif

        if(ret == PV_OK)
        {
            float score = 3.0f;
            XR_Vein_CalcFeatureDist(reg_feat_buf, XR_PALM_FEATURE_SIZE, recg_feat_buf, XR_PALM_FEATURE_SIZE, &score);
            if(score < XR_VEIN_THRESH)
                printf("match success: %.3f\n", score);
            else
                printf("match fail: %.3f\n", score);
        }
        else
        {
            printf("get feature failed: %d\n", ret);
        }

        if(palm_info.status)
        {
            printf("Palm Rect: [x,y,w,h]: %d, %d, %d, %d, palm bright: %d\n", palm_info.x, palm_info.y, palm_info.width, palm_info.height, palm_info.palm_bright);
        }
    }

    delete[] recg_feat_buf;

    return true;
}




int main(int argc, char** argv)
{
    printf("XR CommonVeinPlus API TEST\n");

    char versionBuf[64];
    int32_t version_len = 64;
    int32_t ret = XR_Vein_GetVersion(versionBuf, &version_len);
    printf("Version: %s\n", versionBuf);

    void *alg_handle = NULL;

    ret = XR_Vein_Init(&alg_handle);
    if(ret != PV_OK)
    {
        printf("init failed: %d\n", ret);
        return -1;
    }

    ret = XR_Vein_OpenDev(alg_handle, 0);
    if(ret != PV_OK)
    {
        printf("open dev failed: %d\n", ret);
        XR_Vein_DeInit(alg_handle);
        return -1;
    }

    //get dev info
    int32_t serial_len = 65;
    char serial_num[65];
    memset(serial_num, 0, 65);
    ret = XR_Vein_GetSerialNum(alg_handle, (uint8_t*)serial_num, &serial_len);
    if(ret != PV_OK)
    {
        printf("get serial failed: %d\n", ret);
        XR_Vein_DeInit(alg_handle);
        return -1;
    }
    printf("serial: %s\n", (char*)serial_num);

    int32_t fw_version_len = 65;
    char fw_version[65];
    memset(fw_version, 0, 65);

    ret = XR_Vein_GetFwVersion(alg_handle, fw_version, &fw_version_len);
    if(ret != PV_OK)
    {
        printf("get fw version failed: %d\n", ret);
        XR_Vein_DeInit(alg_handle);
        return -1;
    }
    printf("fw version: %s\n", (char*)fw_version);

    int32_t dev_type = 2;
    ret = XR_Vein_GetDevType(alg_handle, &dev_type);
    if(ret != PV_OK)
    {
        printf("get dev type failed: %d\n", ret);
        XR_Vein_DeInit(alg_handle);
        return -1;
    }
    printf("dev type: %d\n", dev_type);

    int32_t palm_dist = 10;
    ret = XR_Vein_GetPalmDist(alg_handle, &palm_dist);
    if(ret != PV_OK)
    {
        printf("get palm dist failed: %d\n", ret);
        XR_Vein_DeInit(alg_handle);
        return -1;
    }
    printf("palm dist: %d\n", palm_dist);

    int32_t  img_width = 0;
    int32_t  img_height = 0;
    int32_t  img_ch = 0;
    ret = XR_Vein_GetSrcImgSize(alg_handle, &img_width, &img_height, &img_ch);
    if(ret != PV_OK)
    {
        printf("get src img size failed: %d\n", ret);
        XR_Vein_DeInit(alg_handle);
        return -1;
    }
    printf("img_width: %d, img_height: %d, img_ch: %d\n", img_width, img_height, img_ch);

    int32_t feat_size = 0;
    ret = XR_Vein_GetFeatSize(alg_handle, &feat_size);
    if(ret != PV_OK)
    {
        printf("get feat size failed: %d\n", ret);
        XR_Vein_DeInit(alg_handle);
        return -1;
    }
    printf("feat_size: %d\n", feat_size);

    uint8_t *img_buf = new uint8_t[640 * 480];
    for(int32_t i = 0; i < 3; i++)
    {
        int32_t buf_len = 640 * 480;
        ret = XR_Vein_GetStdVeinImage(alg_handle, img_buf, buf_len);
        if(ret != PV_OK)
        {
            printf("cap vein img failed: %d\n", ret);
            break;
        }
        printf("cap img success\n");
        usleep(100*1000);
    }

    //save last img
    FILE *fp = fopen("img.bin", "wb");
    fwrite(img_buf, 1, 640*480, fp);
    fclose(fp);

    ret = XR_Vein_StartEnrollPalm(alg_handle);
    if(ret != PV_OK)
    {
        printf("start enroll failed: %d\n", ret);
        XR_Vein_DeInit(alg_handle);
        return -1;
    }

    bool reg_res = false;
    for(int32_t i = 0; i < 250; i++)
    {
        int32_t enroll_state = 0;
        int32_t cap_tip = 0;
        ret = XR_Vein_GetEnrollState(alg_handle, &enroll_state, &cap_tip);
        if(ret != PV_OK)
        {
            printf("get enroll state failed: %d\n", ret);
            XR_Vein_DeInit(alg_handle);
            return -1;
        }
        printf("enroll state: %d, cap tip: %d\n", enroll_state, cap_tip);
        if(enroll_state == 100)
        {
            reg_res = true;
            printf("enroll success\n");
            break;
        }
        else if(enroll_state == 101)
        {
            break;
        }

        usleep(50*1000);
    }

    if(reg_res == false)
    {
        printf("enroll failed\n");
        XR_Vein_DeInit(alg_handle);
        return -1;
    }

    uint8_t *reg_feat_buf = new uint8_t[XR_PALM_FEATURE_SIZE];
    memset(reg_feat_buf, 0, XR_PALM_FEATURE_SIZE);

    uint8_t *recg_feat_buf = new uint8_t[XR_PALM_FEATURE_SIZE];
    memset(recg_feat_buf, 0, XR_PALM_FEATURE_SIZE);

    int32_t dst_feat_buf_size = XR_PALM_FEATURE_SIZE;

    uint8_t *dst_img_buf = new uint8_t[800 * 600 * 2];
    int32_t dst_img_len = 800 * 600 * 2;


    ret = XR_Vein_FinishEnroll(alg_handle, dst_img_buf, &dst_img_len, reg_feat_buf, &dst_feat_buf_size);
    if(ret != PV_OK)
    {
        printf("export enroll feat failed: %d\n", ret);
        XR_Vein_DeInit(alg_handle);
        return -1;
    }
    printf("get feat success\n");

    //save reroll img
    fp = fopen("enroll_img.bin", "wb");
    fwrite(dst_img_buf, 1, 800*600*2, fp);
    fclose(fp);


    usleep(1*1000);

    //recg feat test
    for(int32_t i = 0; i < 100; i++)
    {
        memset(recg_feat_buf, 0, XR_PALM_FEATURE_SIZE);
        int32_t feat_len = XR_PALM_FEATURE_SIZE;
        int32_t cap_tip = 0;
        ret = XR_Vein_CapRecgFeat(alg_handle, recg_feat_buf, &feat_len, &cap_tip);
        if(ret == PV_OK)
        {
            printf("get feat data\n");
            ret = XR_Vein_CheckFeat(recg_feat_buf,XR_PALM_FEATURE_SIZE);
            if(ret == 0)
            {
                float feat_dist = 3.0f;
                ret = XR_Vein_CalcFeatureDist(reg_feat_buf, XR_PALM_FEATURE_SIZE, recg_feat_buf, XR_PALM_FEATURE_SIZE, &feat_dist);
                if(feat_dist < 0.95f)
                {
                    printf("match success: %.3f\n", feat_dist);
                }
                else
                {
                    printf("match failed: %.3f\n", feat_dist);
                }
            }
            else
            {
                printf("invalid feature\n");
            }
        }
        else
        {
            printf("get feat failed:%d\n", ret);
        }
        usleep(100*1000);
    }



    delete[] reg_feat_buf;
    delete[] recg_feat_buf;
    delete[] img_buf;

    ret = XR_Vein_DeInit(alg_handle);
    if(ret != PV_OK)
    {
        printf("deinit failed: %d\n", ret);
        return -1;
    }

    return 0;
}




