#ifndef XR_VEIN_API_H
#define XR_VEIN_API_H

#include <stdint.h>
#include <xr_ret.h>


#ifdef FVAPI
#undef FVAPI
#endif

#if defined(_WIN32) || defined(_WIN64)
#	define FVAPI __declspec( dllexport )
#	define FVCALL __stdcall
#elif defined(__linux__)
#	define FVAPI   __attribute ((visibility("default")))
#	define FVCALL
#else
#	define FVAPI
#	define FVCALL
#endif

#ifdef __cplusplus
extern "C" {
#endif

/*
* function: Get the SDK version number
* versionBuf: Version number buffer, minimum 64 bytes
* pBufLen: Buffer length, minimum 64 bytes, returns string length if success
* return: Success returns PV_OK, failure returns an error code
 * Example： "xr_common_vein_plus_v2.0.0";
*/

FVAPI int32_t FVCALL XR_Vein_GetVersion(char *pVersionBuf, int32_t *pBufLen);


/*
* function: Initialize SDK
* ppAlgHandle: SDK handle pointer
* return: Success returns PV_OK, failure returns an error code
*/
FVAPI int32_t FVCALL XR_Vein_Init(void **ppDevHandle);

/*
* function: Release SDK handle
* pDevHandle: SDK handle
* return: Success returns PV_OK, failure returns an error code
*/
FVAPI int32_t FVCALL XR_Vein_DeInit(void *pDevHandle);

/*
* function: Get the current number of connected devices
* pDevHandle: SDK handle
* pCnt: Device quantity output pointer
* return: Success returns PV_OK, failure returns an error code
*/
FVAPI int32_t FVCALL XR_Vein_GetDevCnt(void *pDevHandle, int32_t *pCnt);

/*
* function: Turn on the device and activate authorization; without authorization, the registration and identification interfaces cannot be accessed.
* pDevHandle: SDK handle
* idx: Palm vein device serial number: starts from 0; the current version only supports transmitting 0.；
* return: Success returns PV_OK, failure returns an error code
*/
FVAPI int32_t FVCALL XR_Vein_OpenDev(void *pDevHandle, int32_t idx);


/*
* function: Get the type of the current device
* pDevHandle: SDK handle
* pDevType: 0: palm vein device，1：palm vein and palm print device， 2： face and palm vein device
* return: Success returns PV_OK, failure returns an error code
*/
FVAPI int32_t FVCALL XR_Vein_GetDevType(void *pDevHandle, int32_t *pDevType);

/*
* function: Obtain the raw image information of the current device
* pDevHandle: SDK handle
* pImgWidth: Image width information
* pImgHeight: Image height information
* pImgChannel: Image channels；
* return: Success returns PV_OK, failure returns an error code
*/
FVAPI int32_t FVCALL XR_Vein_GetSrcImgSize(void *pDevHandle, int32_t *pImgWidth, int32_t *pImgHeight, int32_t *pImgChannel);

/*
* function: Get the feature value size of the current device
* pDevHandle: SDK handle
* pFeatSize: Current device feature value size
* return: Success returns PV_OK, failure returns an error code
*/
FVAPI int32_t FVCALL XR_Vein_GetFeatSize(void *pDevHandle, int32_t *pFeatSize);


/*
* function: Get the serial number of the current device
* pDevHandle: SDK handle
* pSerialNumBuf: Device serial number buffer
* pBufSize: The input is the buffer size, and the output is the serial number length.
* return: Success returns PV_OK, failure returns an error code
*/
FVAPI int32_t FVCALL XR_Vein_GetSerialNum(void *pDevHandle, uint8_t *pSerialNumBuf, int32_t *pBufSize);


/*
* function: Get the current device firmware version number
* pDevHandle: SDK handle
* pFwVersionBuf: Device firmware version number buffer
* pBufSize: The input is the buffer size, and the output is the length of the device firmware version number
* return: Success returns PV_OK, failure returns an error code
*/
FVAPI int32_t FVCALL XR_Vein_GetFwVersion(void *pDevHandle, char *pFwVersionBuf, int32_t *pBufSize);



/*
* function: Turn off the device
* pDevHandle: SDK handle
* return: Success returns PV_OK, failure returns an error code
*/
FVAPI int32_t FVCALL XR_Vein_CloseDev(void *pDevHandle);


/*
* function: Set the palm module to a low-power mode; in sleep mode, the device turns off the infrared lights and stops the algorithm from running, preventing the execution of registration and recognition logic, which can reduce standby power consumption to some extent.；
 * The device defaults to normal operating mode when turned on; if there is no need for low power consumption, there is no need to set a sleep mode；
* pDevHandle: SDK handle
* state: 1: Enter sleep mode; 0: Exit sleep mode；
* return: Success returns PV_OK, failure returns an error code
*/
FVAPI int32_t FVCALL XR_Vein_SetSleepMode(void *pDevHandle, uint8_t state);


/*
* function: Set the colors of the tri-color lights on the palm module.
* pDevHandle: SDK handle
* r,g,b: The tri-color LED currently only supports being lit; independent brightness control is not supported
* return: Success returns PV_OK, failure returns an error code
*/
FVAPI int32_t FVCALL XR_Vein_SetRgbState(void *pDevHandle, uint8_t r, uint8_t g, uint8_t b);

/*
* function: Adjusting the audio volume of the palm module; only supported by some modules.
* pDevHandle: SDK handle
* soundIdx: Audio volume (0-31)
* return: Success returns PV_OK, failure returns an error code
*/
FVAPI int32_t FVCALL XR_Vein_SetVolume(void *pDevHandle, uint8_t volume);


/*
* function: Setting up audio playback on the palm module; only supported by some modules.
* pDevHandle: SDK handle
* soundIdx: audio sequence
* return: Success returns PV_OK, failure returns an error code
*/
FVAPI int32_t FVCALL XR_Vein_PlayWav(void *pDevHandle, uint8_t soundIdx);


/*
* function: Get the value of the distance between the palm and the device
* pDevHandle: SDK handle
 * pDist：The distance between the palm and the device is measured in millimeters. Distances exceeding 400 millimeters may become inaccurate.
* return: Success returns PV_OK, failure returns an error code
*/
FVAPI int32_t FVCALL XR_Vein_GetPalmDist(void *pDevHandle, int32_t *pDist);


/*
* function: Get the standard palm vein images
* pDevHandle: SDK handle
* pImgBuf： The image buffer for palm veins should be no less than 640×480 pixels. The output image size is: height 640, width 480 pixels.
 * bufLen： Palm image buffer size
* return: Success returns PV_OK, failure returns an error code
*/
FVAPI int32_t FVCALL XR_Vein_GetStdVeinImage(void *pDevHandle, uint8_t *pImgBuf, int32_t bufLen);


/*
 * function: Start registering palm vein
 * pDevHandle: SDK handle
 * return: Success returns PV_OK, failure returns an error code
 */
FVAPI int32_t FVCALL XR_Vein_StartEnrollPalm(void *pDevHandle);

/*
 * function: Enter palm vein image
 * pDevHandle: SDK handle
 * pState: Palm vein entry progress: 100 indicates entry completed, 101 indicates entry failed.
 * pCapTip: Registration prompts
 * return: Success returns PV_OK, failure returns an error code
 */
FVAPI int32_t FVCALL XR_Vein_GetEnrollState(void *pDevHandle, int32_t *pState, int32_t *pCapTip);

/*
 * function: Get the final palm vein features
 * pDevHandle: SDK handle
 * pSrcImgBuf： If the palm vein image buffer is NULL, no image will be returned.
 * pSrcImgBufLen： palm vein image buffer size
 * pRegFeatBuf: Registration feature buffer
 * pBufLen：Not less than 560 bytes
 * return: Success returns PV_OK, failure returns an error code
 */
FVAPI int32_t FVCALL XR_Vein_FinishEnroll(void *pDevHandle, uint8_t *pSrcImgBuf, int32_t *pSrcImgBufLen, uint8_t *pRegFeatBuf, int32_t *pBufLen);


/*
 * function: Obtaining palm vein feature values ​​for authentication
 * pDevHandle: SDK handle
 * pFeatBuf: Features buffer
 * pBufLen：Not less than 560 bytes
 * pCapTip: Collection prompts
 * return: Success returns PV_OK, failure returns an error code
 */
FVAPI int32_t FVCALL XR_Vein_CapRecgFeat(void *pDevHandle, uint8_t *pFeatBuf, int32_t *pBufLen, int32_t *pCapTip);



/*
 * function: Palm vein features detected and extracted from the original image
 * pDevHandle: SDK handle
 * pImgBuf: Input palm vein image
 * imgRows, imgCols: Input image height and width
 * pRegFeatBuf: Features buffer
 * pBufLen：Not less than 560 bytes
 * pCapTip: Recognition prompts
 * pPalmInfo: Palm detection information: a non-zero status value indicates successful detection.
 * return: Success returns PV_OK, failure returns an error code
 */
FVAPI int32_t FVCALL XR_Vein_GrabFeatureFromFullImg(void *pDevHandle, uint8_t *pImgBuf, int32_t imgRows, int32_t imgCols, uint8_t *pFeatBuf, int32_t *pBufLen);


/*
 * function: Verify the validity of palm vein features
 * pRegFeatBuf: Palm vein features buffer
 * bufLen：Palm vein buffer length
 * return: Success returns PV_OK, failure returns an error code
 */
FVAPI int32_t FVCALL XR_Vein_CheckFeat(uint8_t *pFeatBuf, int32_t bufLen);


/*
 * function: Compare the distances between palm vein features
 * pFeatBuf1: Palm vein feature buffer 1
 * bufLen1： Palm vein feature buffer 1 length
 * pFeatBuf2: Palm vein feature buffer 2
 * bufLen2: Palm vein feature buffer 2 length
 * pDist： For palm vein feature comparison, the threshold should be between 0.9 and 1.0, with a recommended threshold of 0.95f;
 */
FVAPI int32_t FVCALL XR_Vein_CalcFeatureDist(uint8_t *pFeatBuf1, int32_t bufLen1, uint8_t *pFeatBuf2, int32_t bufLen2, float *pDist);


/*
 * function: Palm vein feature value format conversion, used for Android SDK feature value conversion.
 * pFeature: Raw palm vein features, such as those captured from an Android device.
 * len1: Length of raw palm vein features
 * pMyFeature: Local palm vein (target features)
 * len2: Length of local palm vein features
 */
FVAPI int32_t FVCALL XR_Vein_fp32FeatureToMyFeature(uint8_t* pSrcFeature, int len1, uint8_t* pDstFeature, int len2);

#ifdef __cplusplus
}
#endif





#endif
