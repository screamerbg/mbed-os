/*******************************************************************************
 * Copyright 2016, 2017 ARM Ltd.
 *
 * Licensed under the Apache License, Version 2.0 (the "License");
 * you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 *     http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 *******************************************************************************/


#ifndef _PAL_PLAT_DRBG_H
#define _PAL_PLAT_DRBG_H

#ifdef __cplusplus
extern "C" {
#endif

#include "pal.h"
    

/*! \file pal_plat_rtos.h
*  \brief PAL RTOS - platform.
*   This file contains the real-time OS APIs that need to be implemented in the platform layer.
*/



/*! Initialize all data structures (semaphores, mutexes, memory pools, message queues) at system initialization.
*   In case of a failure in any of the initializations, the function returns an error and stops the rest of the initializations.
* @param[in] opaqueContext The context passed to the initialization (not required for generic CMSIS, pass NULL in this case).
* \return PAL_SUCCESS(0) in case of success, PAL_ERR_CREATION_FAILED in case of failure.
*/
palStatus_t pal_plat_DRBGInit();

/*! De-initialize thread objects.
*/
palStatus_t pal_plat_DRBGDestroy(void);

// XXX: following two are really easy to mix up, a better naming needs to be done
//
// * pal_plat_osRandomBuffer_public() - The one which is called by pal_osRandomBuffer(), one which
//                                      will block until there is enough entropy harvested
//
// * pal_plat_osRandomBuffer() - The lower level part, used by pal_plat_osRandomBuffer_public(),
//                                  this is nonblocking version which will return as much as possible.
//                               Perhaps this should be pal_plat_GetosRandomBufferFromHW() to align
//                               with logic used with similar purpose function as pal_plat_osGetRoTFromHW().

/*! Generate a random number into the given buffer with the given size in bytes.
*
* @param[out] randomBuf A buffer to hold the generated number.
* @param[in] bufSizeBytes The size of the buffer and the size of the required random number to generate.
* @param[out] actualRandomSizeBytes The actual size of the written random data to the output buffer.
\return PAL_SUCCESS on success. A negative value indicating a specific error code in case of failure.
\note In case the platform was able to provide random data with non-zero size and less than `bufSizeBytes`the function must return `PAL_ERR_RTOS_TRNG_PARTIAL_DATA`
*/
palStatus_t pal_plat_osRandomBuffer(uint8_t *randomBuf, size_t bufSizeBytes, size_t* actualRandomSizeBytes);

/*! Generate random number into given buffer with given size in bytes.
*
* @param[out] randomBuf A buffer to hold the generated number.
* @param[in] bufSizeBytes The size of the buffer and the size of the required random number to generate.
*
\note `pal_init()` MUST be called before this function
\return PAL_SUCCESS on success, a negative value indicating a specific error code in case of failure.
*/
palStatus_t pal_plat_osRandomBuffer_blocking(uint8_t *randomBuf, size_t bufSizeBytes);

#ifdef __cplusplus
}
#endif
#endif //_PAL_PLAT_RTOS_H
