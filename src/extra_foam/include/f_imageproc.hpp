/**
 * Distributed under the terms of the BSD 3-Clause License.
 *
 * The full license is in the file LICENSE, distributed with this software.
 *
 * Author: Jun Zhu <jun.zhu@xfel.eu>
 * Copyright (C) European X-Ray Free-Electron Laser Facility GmbH.
 * All rights reserved.
 */
#ifndef EXTRA_FOAM_IMAGE_PROC_H
#define EXTRA_FOAM_IMAGE_PROC_H

#include <type_traits>

#include "xtensor/xview.hpp"
#include "xtensor/xmath.hpp"
#include "xtensor/xindex_view.hpp"

#if defined(FOAM_WITH_TBB)
#include "tbb/parallel_for.h"
#include "tbb/blocked_range2d.h"
#include "tbb/blocked_range3d.h"
#endif

#include "f_traits.hpp"
#include "f_utilities.hpp"


namespace foam
{

#if defined(FOAM_WITH_TBB)
namespace detail
{

template<typename E>
inline auto nanmeanImageArrayImp(E&& src, const std::vector<size_t>& keep = {})
{
  using value_type = typename std::decay_t<E>::value_type;
  auto shape = src.shape();

  // a bit hacky
  using return_type = decltype(xt::eval(xt::sum<value_type>(std::declval<E>(), {0})));
  auto mean = return_type::from_shape({static_cast<std::size_t>(shape[1]),
                                       static_cast<std::size_t>(shape[2])});

  tbb::parallel_for(tbb::blocked_range2d<int>(0, shape[1], 0, shape[2]),
    [&src, &keep, &shape, &mean] (const tbb::blocked_range2d<int> &block)
    {
      for(int j=block.rows().begin(); j != block.rows().end(); ++j)
      {
        for(int k=block.cols().begin(); k != block.cols().end(); ++k)
        {
          std::size_t count = 0;
          value_type sum = 0;
          if (keep.empty())
          {
            for (auto i=0; i<shape[0]; ++i)
            {
              auto v = src(i, j, k);
              if (! std::isnan(v))
              {
                count += 1;
                sum += v;
              }
            }
          } else
          {
            for (auto it=keep.begin(); it != keep.end(); ++it)
            {
              auto v = src(*it, j, k);
              if (! std::isnan(v))
              {
                count += 1;
                sum += v;
              }
            }
          }

          if (count == 0)
            mean(j, k) = std::numeric_limits<value_type>::quiet_NaN();
          else mean(j, k) = sum / value_type(count);
        }
      }
    }
  );

  return mean;
}

} // detail
#endif

/**
 * Calculate the nanmean of the selected images from an array of images.
 *
 * @param src: image data. shape = (indices, y, x)
 * @param keep: a list of selected indices.
 * @return: the nanmean image. shape = (y, x)
 */
template<typename E, EnableIf<std::decay_t<E>, IsImageArray> = false>
inline auto nanmeanImageArray(E&& src, const std::vector<size_t>& keep)
{
#if defined(FOAM_WITH_TBB)
  if (keep.empty()) throw std::invalid_argument("keep cannot be empty!");
  return detail::nanmeanImageArrayImp(std::forward<E>(src), keep);
#else
  using value_type = typename std::decay_t<E>::value_type;
  auto&& sliced(xt::view(std::forward<E>(src), xt::keep(keep), xt::all(), xt::all()));
  return xt::eval(xt::nanmean<value_type>(sliced, 0));
#endif
}

template<typename E, EnableIf<std::decay_t<E>, IsImageArray> = false>
inline auto nanmeanImageArray(E&& src)
{
#if defined(FOAM_WITH_TBB)
  return detail::nanmeanImageArrayImp(std::forward<E>(src));
#else
  using value_type = typename std::decay_t<E>::value_type;
  return xt::eval(xt::nanmean<value_type>(std::forward<E>(src), 0));
#endif
}

/**
 * Calculate the nanmean of two images.
 *
 * @param src1: image data. shape = (y, x)
 * @param src2: image data. shape = (y, x)
 * @return: the nanmean image. shape = (y, x)
 */
template<typename E>
inline auto nanmeanImageArray(E&& src1, E&& src2)
{
  using value_type = typename std::decay_t<E>::value_type;
  auto shape = src1.shape();

  checkShape(shape, src2.shape(), "Images have different shapes");

#if defined(FOAM_WITH_TBB)
  auto mean = std::decay_t<E>({shape[0], shape[1]});

  tbb::parallel_for(tbb::blocked_range2d<int>(0, shape[0], 0, shape[1]),
    [&src1, &src2, &shape, &mean] (const tbb::blocked_range2d<int> &block)
    {
      for(int j=block.rows().begin(); j != block.rows().end(); ++j)
      {
        for(int k=block.cols().begin(); k != block.cols().end(); ++k)
        {
          auto x = src1(j, k);
          auto y = src2(j, k);

          if (std::isnan(x) and std::isnan(y))
            mean(j, k) = std::numeric_limits<value_type>::quiet_NaN();
          else if (std::isnan(x))
            mean(j, k) = y;
          else if (std::isnan(y))
            mean(j, k) = x;
          else mean(j, k)  = value_type(0.5) * (x + y);
        }
      }
    }
  );

  return mean;
#else
  auto&& stacked = xt::stack(xt::xtuple(std::forward<E>(src1), std::forward<E>(src2)));
  return xt::eval(xt::nanmean<value_type>(stacked, 0));
#endif
}

/**
 * Inplace convert nan using 0 in an image.
 *
 * @param src: image data. shape = (y, x)
 */
template <typename E, EnableIf<E, IsImage> = false>
inline void maskImageDataZero(E& src)
{
  using value_type = typename E::value_type;
  auto shape = src.shape();

  for (size_t j = 0; j < shape[0]; ++j)
  {
    for (size_t k = 0; k < shape[1]; ++k)
    {
      if (std::isnan(src(j, k))) src(j, k) = value_type(0);
    }
  }
}

/**
 * Maintain an identical API with maskImageDataZero.
 *
 * @param src: image data. shape = (y, x)
 */
template <typename E, EnableIf<E, IsImage> = false>
inline void maskImageDataNan(E& src) {}

/**
 * Get the nan mask of an image.
 *
 * This function is a complementary to maskImageDataNan since the overload
 * maskImageDataNan(E& src, N& out) is ambiguous because of another overload
 * maskImageDataNan(E& src, const M& mask).
 *
 * @param src: image data. shape = (y, x)
 * @param out: output array to place the mask. shape = (y, x)
 */
template <typename E, typename N, EnableIf<E, IsImage> = false, EnableIf<N, IsImageMask> = false>
inline void imageDataNanMask(const E& src, N& out)
{
  using value_type = typename E::value_type;
  auto shape = src.shape();

  checkShape(shape, out.shape(), "Image and output array have different shapes");

  for (size_t j = 0; j < shape[0]; ++j)
  {
    for (size_t k = 0; k < shape[1]; ++k)
    {
      if (std::isnan(src(j, k))) out(j, k) = true;
    }
  }
}

/**
 * Inplace mask an image using 0 with threshold mask. Nan pixels in
 * the image are also converted into 0.
 *
 * @param src: image data. shape = (y, x)
 * @param lb: lower threshold
 * @param ub: upper threshold
 */
template <typename E, typename T,
  EnableIf<E, IsImage> = false, std::enable_if_t<std::is_arithmetic<T>::value, bool> = false>
inline void maskImageDataZero(E& src, T lb, T ub)
{
  using value_type = typename E::value_type;
  auto shape = src.shape();

  auto nan = std::numeric_limits<value_type>::quiet_NaN();
  for (size_t j = 0; j < shape[0]; ++j)
  {
    for (size_t k = 0; k < shape[1]; ++k)
    {
      auto v = src(j, k);
      if (std::isnan(v) || v < lb || v > ub) src(j, k) = value_type(0);
    }
  }
}

/**
 * Inplace mask an image using 0 with threshold mask. Nan pixels in
 * the image are also converted into 0.
 *
 * @param src: image data. shape = (y, x)
 * @param lb: lower threshold
 * @param ub: upper threshold
 * @param out: output array to place the overall mask. shape = (y, x)
 */
template <typename E, typename T, typename N,
  EnableIf<E, IsImage> = false, std::enable_if_t<std::is_arithmetic<T>::value, bool> = false,
  EnableIf<N, IsImageMask> = false>
inline void maskImageDataZero(E& src, T lb, T ub, N& out)
{
  using value_type = typename E::value_type;
  auto shape = src.shape();

  checkShape(shape, out.shape(), "Image and output array have different shapes");

  auto nan = std::numeric_limits<value_type>::quiet_NaN();
  for (size_t j = 0; j < shape[0]; ++j)
  {
    for (size_t k = 0; k < shape[1]; ++k)
    {
      auto v = src(j, k);
      if (std::isnan(v) || v < lb || v > ub)
      {
        src(j, k) = value_type(0);
        out(j, k) = true;
      }
    }
  }
}

/**
 * Inplace mask an image using nan with threshold mask.
 *
 * @param src: image data. shape = (y, x)
 * @param lb: lower threshold
 * @param ub: upper threshold
 */
template <typename E, typename T,
  EnableIf<E, IsImage> = false, std::enable_if_t<std::is_arithmetic<T>::value, bool> = false>
inline void maskImageDataNan(E& src, T lb, T ub)
{
  using value_type = typename E::value_type;
  auto shape = src.shape();

  auto nan = std::numeric_limits<value_type>::quiet_NaN();
  for (size_t j = 0; j < shape[0]; ++j)
  {
    for (size_t k = 0; k < shape[1]; ++k)
    {
      auto v = src(j, k);
      if (std::isnan(v)) continue;
      if (v < lb || v > ub) src(j, k) = nan;
    }
  }
}

/**
 * Inplace mask an image using nan with threshold mask.
 *
 * @param src: image data. shape = (y, x)
 * @param lb: lower threshold
 * @param ub: upper threshold
 * @param out: output array to place the overall mask. shape = (y, x)
 */
template <typename E, typename T, typename N,
  EnableIf<E, IsImage> = false, std::enable_if_t<std::is_arithmetic<T>::value, bool> = false,
  EnableIf<N, IsImageMask> = false>
inline void maskImageDataNan(E& src, T lb, T ub, N& out)
{
  using value_type = typename E::value_type;
  auto shape = src.shape();

  checkShape(shape, out.shape(), "Image and output array have different shapes");

  auto nan = std::numeric_limits<value_type>::quiet_NaN();
  for (size_t j = 0; j < shape[0]; ++j)
  {
    for (size_t k = 0; k < shape[1]; ++k)
    {
      auto v = src(j, k);
      if (std::isnan(v)) out(j, k) = true;
      else if (v < lb || v > ub)
      {
        src(j, k) = nan;
        out(j, k) = true;
      }
    }
  }
}

/**
 * Inplace mask an image using 0 with an image mask. Nan pixels in
 * the image are also converted into 0.
 *
 * @param src: image data. shape = (y, x)
 * @param mask: image mask. shape = (y, x)
 */
template <typename E, typename M,
  EnableIf<E, IsImage> = false, EnableIf<M, IsImageMask> = false>
inline void maskImageDataZero(E& src, const M& mask)
{
  using value_type = typename E::value_type;
  auto shape = src.shape();

  checkShape(shape, mask.shape(), "Image and mask have different shapes");

  auto nan = std::numeric_limits<value_type>::quiet_NaN();
  for (size_t j = 0; j < shape[0]; ++j)
  {
    for (size_t k = 0; k < shape[1]; ++k)
    {
      if (mask(j, k) || std::isnan(src(j, k))) src(j, k) = value_type(0);
    }
  }
}

/**
 * Inplace mask an image using 0 with an image mask. Nan pixels in
 * the image are also converted into 0.
 *
 * @param src: image data. shape = (y, x)
 * @param mask: image mask. shape = (y, x)
 * @param out: output array to place the overall mask. shape = (y, x)
 */
template <typename E, typename M, typename N,
  EnableIf<E, IsImage> = false, EnableIf<M, IsImageMask> = false, EnableIf<N, IsImageMask> = false>
inline void maskImageDataZero(E& src, const M& mask, M& out)
{
  using value_type = typename E::value_type;
  auto shape = src.shape();

  checkShape(shape, mask.shape(), "Image and mask have different shapes");
  checkShape(shape, out.shape(), "Image and output array have different shapes");

  auto nan = std::numeric_limits<value_type>::quiet_NaN();
  for (size_t j = 0; j < shape[0]; ++j)
  {
    for (size_t k = 0; k < shape[1]; ++k)
    {
      if (mask(j, k) || std::isnan(src(j, k)))
      {
        src(j, k) = value_type(0);
        out(j, k) = true;
      }
    }
  }
}

/**
 * Inplace mask an image using nan with an image mask.
 *
 * @param src: image data. shape = (y, x)
 * @param mask: image mask. shape = (y, x)
 */
template <typename E, typename M,
  EnableIf<E, IsImage> = false, EnableIf<M, IsImageMask> = false>
inline void maskImageDataNan(E& src, const M& mask)
{
  using value_type = typename E::value_type;
  auto shape = src.shape();

  checkShape(shape, mask.shape(), "Image and mask have different shapes");

  auto nan = std::numeric_limits<value_type>::quiet_NaN();
  for (size_t j = 0; j < shape[0]; ++j)
  {
    for (size_t k = 0; k < shape[1]; ++k)
    {
      if (mask(j, k)) src(j, k) = nan;
    }
  }
}

/**
 * Inplace mask an image using nan with an image mask.
 *
 * @param src: image data. shape = (y, x)
 * @param out: output array to place the overall mask. shape = (y, x)
 */
template <typename E, typename M, typename N,
  EnableIf<E, IsImage> = false, EnableIf<M, IsImageMask> = false, EnableIf<N, IsImageMask> = false>
inline void maskImageDataNan(E& src, const M& mask, N& out)
{
  using value_type = typename E::value_type;
  auto shape = src.shape();

  checkShape(shape, mask.shape(), "Image and mask have different shapes");
  checkShape(shape, out.shape(), "Image and output array have different shapes");

  auto nan = std::numeric_limits<value_type>::quiet_NaN();
  for (size_t j = 0; j < shape[0]; ++j)
  {
    for (size_t k = 0; k < shape[1]; ++k)
    {
      if (std::isnan(src(j, k)))
      {
        out(j, k) = true;
      } else if (mask(j, k))
      {
        src(j, k) = nan;
        out(j, k) = nan;
      }
    }
  }
}

/**
 * Inplace mask an image using 0 with both threshold mask and an image mask.
 * Nan pixels in the image are also converted into 0.
 *
 * @param src: image data. shape = (y, x)
 * @param mask: image mask. shape = (y, x)
 * @param lb: lower threshold
 * @param ub: upper threshold
 */
template <typename E, typename M, typename T,
  EnableIf<E, IsImage> = false, EnableIf<M, IsImageMask> = false,
  std::enable_if_t<std::is_arithmetic<T>::value, bool> = false>
inline void maskImageDataZero(E& src, const M& mask, T lb, T ub)
{
  using value_type = typename E::value_type;
  auto shape = src.shape();

  checkShape(shape, mask.shape(), "Image and mask have different shapes");

  auto nan = std::numeric_limits<value_type>::quiet_NaN();
  for (size_t j = 0; j < shape[0]; ++j)
  {
    for (size_t k = 0; k < shape[1]; ++k)
    {
      if (mask(j, k)) src(j, k) = value_type(0);
      else
      {
        auto v = src(j, k);
        if (std::isnan(v) || v < lb || v > ub) src(j, k) = value_type(0);
      }
    }
  }
}

/**
 * Inplace mask an image using 0 with both threshold mask and an image mask.
 * Nan pixels in the image are also converted into 0.
 *
 * @param src: image data. shape = (y, x)
 * @param mask: image mask. shape = (y, x)
 * @param lb: lower threshold
 * @param ub: upper threshold
 * @param out: output array to place the overall mask. shape = (y, x)
 */
template <typename E, typename M, typename T, typename N,
  EnableIf<E, IsImage> = false, EnableIf<M, IsImageMask> = false, EnableIf<N, IsImageMask> = false>
inline void maskImageDataZero(E& src, const M& mask, T lb, T ub, N& out)
{
  using value_type = typename E::value_type;
  auto shape = src.shape();

  checkShape(shape, mask.shape(), "Image and mask have different shapes");
  checkShape(shape, out.shape(), "Image and output array have different shapes");

  auto nan = std::numeric_limits<value_type>::quiet_NaN();
  for (size_t j = 0; j < shape[0]; ++j)
  {
    for (size_t k = 0; k < shape[1]; ++k)
    {
      if (mask(j, k))
      {
        src(j, k) = value_type(0);
        out(j, k) = true;
      } else
      {
        auto v = src(j, k);
        if (std::isnan(v) || v < lb || v > ub)
        {
          src(j, k) = value_type(0);
          out(j, k) = true;
        }
      }
    }
  }
}

/**
 * Inplace mask an image using nan with both threshold mask and an image mask.
 *
 * @param src: image data. shape = (y, x)
 * @param mask: image mask. shape = (y, x)
 * @param lb: lower threshold
 * @param ub: upper threshold
 */
template <typename E, typename M, typename T,
  EnableIf<E, IsImage> = false, EnableIf<M, IsImageMask> = false,
  std::enable_if_t<std::is_arithmetic<T>::value, bool> = false>
inline void maskImageDataNan(E& src, const M& mask, T lb, T ub)
{
  using value_type = typename E::value_type;
  auto shape = src.shape();

  checkShape(shape, mask.shape(), "Image and mask have different shapes");

  auto nan = std::numeric_limits<value_type>::quiet_NaN();
  for (size_t j = 0; j < shape[0]; ++j)
  {
    for (size_t k = 0; k < shape[1]; ++k)
    {
      if (mask(j, k)) src(j, k) = nan;
      else
      {
        auto v = src(j, k);
        if (std::isnan(v)) continue;
        if (v < lb || v > ub) src(j, k) = nan;
      }
    }
  }
}

/**
 * Inplace mask an image using nan with both threshold mask and an image mask.
 *
 * @param src: image data. shape = (y, x)
 * @param lb: lower threshold
 * @param ub: upper threshold
 * @param out: output array to place the overall mask. shape = (y, x)
 */
template <typename E, typename M, typename T, typename N,
  EnableIf<E, IsImage> = false, EnableIf<M, IsImageMask> = false, EnableIf<N, IsImageMask> = false>
inline void maskImageDataNan(E& src, const M& mask, T lb, T ub, N& out)
{
  using value_type = typename E::value_type;
  auto shape = src.shape();

  checkShape(shape, mask.shape(), "Image and mask have different shapes");
  checkShape(shape, out.shape(), "Image and output array have different shapes");

  auto nan = std::numeric_limits<value_type>::quiet_NaN();
  for (size_t j = 0; j < shape[0]; ++j)
  {
    for (size_t k = 0; k < shape[1]; ++k)
    {
      auto v = src(j, k);
      if (mask(j, k))
      {
        src(j, k) = nan;
        out(j, k) = true;
      } else if (std::isnan(v))
      {
        out(j, k) = true;
      } else if (v < lb || v > ub)
      {
        src(j, k) = nan;
        out(j, k) = true;
      }
    }
  }
}

/**
 * Inplace convert nan using 0 in an array of images.
 *
 * @param src: image data. shape = (indices, y, x)
 */
template <typename E, EnableIf<E, IsImageArray> = false>
inline void maskImageDataZero(E& src)
{
  using value_type = typename E::value_type;
  auto shape = src.shape();

#if defined(FOAM_WITH_TBB)
  tbb::parallel_for(tbb::blocked_range3d<int>(0, shape[0], 0, shape[1], 0, shape[2]),
    [&src] (const tbb::blocked_range3d<int> &block)
    {
      for(int i=block.pages().begin(); i != block.pages().end(); ++i)
      {
        for(int j=block.rows().begin(); j != block.rows().end(); ++j)
        {
          for(int k=block.cols().begin(); k != block.cols().end(); ++k)
          {
            if (std::isnan(src(i, j, k))) src(i, j, k) = value_type(0);
          }
        }
      }
    }
  );
#else
  xt::filter(src, xt::isnan(src)) = value_type(0);
#endif
}

/**
 * Maintain an identical API with maskImageDataZero.
 *
 * @param src: image data. shape = (indices, y, x)
 */
template <typename E, EnableIf<E, IsImageArray> = false>
inline void maskImageDataNan(E& src) {}

/**
 * Inplace mask an array of images using 0 with threshold mask. Nan pixels in
 * those images are also converted into 0.
 *
 * @param src: image data. shape = (slices, y, x)
 * @param lb: lower threshold
 * @param ub: upper threshold
 */
template <typename E, typename T,
  EnableIf<E, IsImageArray> = false, std::enable_if_t<std::is_arithmetic<T>::value, bool> = false>
inline void maskImageDataZero(E& src, T lb, T ub)
{
  using value_type = typename E::value_type;
#if defined(FOAM_WITH_TBB)
  auto shape = src.shape();

  auto nan = std::numeric_limits<value_type>::quiet_NaN();
  tbb::parallel_for(tbb::blocked_range3d<int>(0, shape[0], 0, shape[1], 0, shape[2]),
    [&src, lb, ub, nan] (const tbb::blocked_range3d<int> &block)
    {
      for(int i=block.pages().begin(); i != block.pages().end(); ++i)
      {
        for(int j=block.rows().begin(); j != block.rows().end(); ++j)
        {
          for(int k=block.cols().begin(); k != block.cols().end(); ++k)
          {
            auto v = src(i, j, k);
            if (std::isnan(v) || v < lb || v > ub) src(i, j, k) = value_type(0);
          }
        }
      }
    }
  );
#else
  xt::filter(src, xt::isnan(src) | src < lb | src > ub) = value_type(0);
#endif
}

/**
 * Inplace mask an array of images using nan with threshold mask.
 *
 * @param src: image data. shape = (slices, y, x)
 * @param lb: lower threshold
 * @param ub: upper threshold
 */
template <typename E, typename T,
  EnableIf<E, IsImageArray> = false, std::enable_if_t<std::is_arithmetic<T>::value, bool> = false>
inline void maskImageDataNan(E& src, T lb, T ub)
{
  using value_type = typename E::value_type;

  auto nan = std::numeric_limits<value_type>::quiet_NaN();
#if defined(FOAM_WITH_TBB)
  auto shape = src.shape();

  tbb::parallel_for(tbb::blocked_range3d<int>(0, shape[0], 0, shape[1], 0, shape[2]),
    [&src, lb, ub, nan] (const tbb::blocked_range3d<int> &block)
    {
      for(int i=block.pages().begin(); i != block.pages().end(); ++i)
      {
        for(int j=block.rows().begin(); j != block.rows().end(); ++j)
        {
          for(int k=block.cols().begin(); k != block.cols().end(); ++k)
          {
            auto v = src(i, j, k);
            if (std::isnan(v)) continue;
            if (v < lb || v > ub) src(i, j, k) = nan;
          }
        }
      }
    }
  );
#else
  xt::filter(src, src < lb | src > ub) = nan;
#endif
}

/**
 * Inplace mask an array of images using 0 with an image mask. Nan pixels in
 * those images are also converted into 0.
 *
 * @param src: image data. shape = (indices, y, x)
 * @param mask: image mask. shape = (y, x)
 */
template <typename E, typename M,
  EnableIf<E, IsImageArray> = false, EnableIf<M, IsImageMask> = false>
inline void maskImageDataZero(E& src, const M& mask)
{
  using value_type = typename E::value_type;
  auto shape = src.shape();

  checkShape(shape, mask.shape(), "Image and mask have different shapes", 1);

  auto nan = std::numeric_limits<value_type>::quiet_NaN();
#if defined(FOAM_WITH_TBB)
  tbb::parallel_for(tbb::blocked_range3d<int>(0, shape[0], 0, shape[1], 0, shape[2]),
    [&src, &mask, nan] (const tbb::blocked_range3d<int> &block)
    {
      for(int i=block.pages().begin(); i != block.pages().end(); ++i)
      {
        for(int j=block.rows().begin(); j != block.rows().end(); ++j)
        {
          for(int k=block.cols().begin(); k != block.cols().end(); ++k)
          {
#else
      for (size_t i = 0; i < shape[0]; ++i)
      {
        for (size_t j = 0; j < shape[1]; ++j)
        {
          for (size_t k = 0; k < shape[2]; ++k)
          {
#endif
            if (mask(j, k) || std::isnan(src(i, j, k))) src(i, j, k) = value_type(0);
          }
        }
      }
#if defined(FOAM_WITH_TBB)
    }
  );
#endif
}

/**
 * Inplace mask an array of images using nan with an image mask.
 *
 * @param src: image data. shape = (indices, y, x)
 * @param mask: image mask. shape = (y, x)
 */
template <typename E, typename M,
  EnableIf<E, IsImageArray> = false, EnableIf<M, IsImageMask> = false>
inline void maskImageDataNan(E& src, const M& mask)
{
  using value_type = typename E::value_type;
  auto shape = src.shape();

  checkShape(shape, mask.shape(), "Image and mask have different shapes", 1);

  auto nan = std::numeric_limits<value_type>::quiet_NaN();
#if defined(FOAM_WITH_TBB)
  tbb::parallel_for(tbb::blocked_range3d<int>(0, shape[0], 0, shape[1], 0, shape[2]),
    [&src, &mask, nan] (const tbb::blocked_range3d<int> &block)
    {
      for(int i=block.pages().begin(); i != block.pages().end(); ++i)
      {
        for(int j=block.rows().begin(); j != block.rows().end(); ++j)
        {
          for(int k=block.cols().begin(); k != block.cols().end(); ++k)
          {
#else
      for (size_t i = 0; i < shape[0]; ++i)
      {
        for (size_t j = 0; j < shape[1]; ++j)
        {
          for (size_t k = 0; k < shape[2]; ++k)
          {
#endif
            if (mask(j, k)) src(i, j, k) = nan;
          }
        }
      }
#if defined(FOAM_WITH_TBB)
    }
  );
#endif
}

/**
 * Inplace mask an array of images using 0 with both threshold mask and an image mask.
 * Nan pixels in those images are also converted into 0.
 *
 * @param src: image data. shape = (indices, y, x)
 * @param mask: image mask. shape = (y, x)
 */
template <typename E, typename M, typename T,
  EnableIf<E, IsImageArray> = false, EnableIf<M, IsImageMask> = false>
inline void maskImageDataZero(E& src, const M& mask, T lb, T ub)
{
  using value_type = typename E::value_type;
  auto shape = src.shape();

  checkShape(shape, mask.shape(), "Image and mask have different shapes", 1);

  auto nan = std::numeric_limits<value_type>::quiet_NaN();
#if defined(FOAM_WITH_TBB)
  tbb::parallel_for(tbb::blocked_range3d<int>(0, shape[0], 0, shape[1], 0, shape[2]),
    [&src, &mask, lb, ub, nan] (const tbb::blocked_range3d<int> &block)
    {
      for(int i=block.pages().begin(); i != block.pages().end(); ++i)
      {
        for(int j=block.rows().begin(); j != block.rows().end(); ++j)
        {
          for(int k=block.cols().begin(); k != block.cols().end(); ++k)
          {
#else
      for (size_t i = 0; i < shape[0]; ++i)
      {
        for (size_t j = 0; j < shape[1]; ++j)
        {
          for (size_t k = 0; k < shape[2]; ++k)
          {
#endif
            if (mask(j, k))
            {
              src(i, j, k) = value_type(0);
            } else
            {
              auto v = src(i, j, k);
              if (std::isnan(v) || v < lb || v > ub) src(i, j, k) = value_type(0);
            }
          }
        }
      }
#if defined(FOAM_WITH_TBB)
    }
  );
#endif
}

/**
 * Inplace mask an array of images using nan with both threshold mask and an image mask.
 *
 * @param src: image data. shape = (indices, y, x)
 * @param mask: image mask. shape = (y, x)
 */
template <typename E, typename M, typename T,
  EnableIf<E, IsImageArray> = false, EnableIf<M, IsImageMask> = false>
inline void maskImageDataNan(E& src, const M& mask, T lb, T ub)
{
  using value_type = typename E::value_type;
  auto shape = src.shape();

  checkShape(shape, mask.shape(), "Image and mask have different shapes", 1);

  auto nan = std::numeric_limits<value_type>::quiet_NaN();
#if defined(FOAM_WITH_TBB)
  tbb::parallel_for(tbb::blocked_range3d<int>(0, shape[0], 0, shape[1], 0, shape[2]),
    [&src, &mask, lb, ub, nan] (const tbb::blocked_range3d<int> &block)
    {
      for(int i=block.pages().begin(); i != block.pages().end(); ++i)
      {
        for(int j=block.rows().begin(); j != block.rows().end(); ++j)
        {
          for(int k=block.cols().begin(); k != block.cols().end(); ++k)
          {
#else
      for (size_t i = 0; i < shape[0]; ++i)
      {
        for (size_t j = 0; j < shape[1]; ++j)
        {
          for (size_t k = 0; k < shape[2]; ++k)
          {
#endif
            if (mask(j, k))
            {
              src(i, j, k) = nan;
            } else
            {
              auto v = src(i, j, k);
              if (std::isnan(v)) continue;
              if (v < lb || v > ub) src(i, j, k) = nan;
            }
          }
        }
      }
#if defined(FOAM_WITH_TBB)
    }
  );
#endif
}

/**
 * Inplace apply moving average for an image
 *
 * @param src: moving average of image data. shape = (y, x)
 * @param data: new image data. shape = (y, x)
 * @param count: new moving average count.
 */
template <typename E, EnableIf<E, IsImage> = false>
inline void movingAvgImageData(E& src, const E& data, size_t count)
{
  if (count == 0) throw std::invalid_argument("'count' cannot be zero!");

  using value_type = typename E::value_type;
  auto shape = src.shape();

  checkShape(shape, data.shape(), "Inconsistent data shapes");

  for (size_t j = 0; j < shape[0]; ++j)
  {
    for (size_t k = 0; k < shape[1]; ++k)
    {
      src(j, k) += (data(j, k) - src(j, k)) / value_type(count);
    }
  }
}

/**
 * Inplace apply moving average for an array of images.
 *
 * @param src: moving average of image data. shape = (indices, y, x)
 * @param data: new image data. shape = (indices, y, x)
 * @param count: new moving average count.
 */
template <typename E, EnableIf<E, IsImageArray> = false>
inline void movingAvgImageData(E& src, const E& data, size_t count)
{
  if (count == 0) throw std::invalid_argument("'count' cannot be zero!");

  using value_type = typename E::value_type;
  auto shape = src.shape();

  checkShape(shape, data.shape(), "Inconsistent data shapes");

#if defined(FOAM_WITH_TBB)
  tbb::parallel_for(tbb::blocked_range3d<int>(0, shape[0], 0, shape[1], 0, shape[2]),
    [&src, &data, count] (const tbb::blocked_range3d<int> &block)
    {
      for(int i=block.pages().begin(); i != block.pages().end(); ++i)
      {
        for(int j=block.rows().begin(); j != block.rows().end(); ++j)
        {
          for(int k=block.cols().begin(); k != block.cols().end(); ++k)
          {
#else
      for (size_t i = 0; i < shape[0]; ++i)
      {
        for (size_t j = 0; j < shape[1]; ++j)
        {
          for (size_t k = 0; k < shape[2]; ++k)
          {
#endif
            src(i, j, k) += (data(i, j, k) - src(i, j, k)) / value_type(count);
          }
        }
      }
#if defined(FOAM_WITH_TBB)
    }
  );
#endif
}

class OffsetPolicy {
public:
  template<typename T>
  static T correct(T v, T a) {
    return v - a;
  }
};

class GainPolicy {
public:
  template<typename T>
  static T correct(T v, T a) {
    return v * a;
  }
};

/**
 * Inplace apply either gain or offset correct for an array of images.
 *
 * @tparam Policy: correction policy (OffsetPolicy or GainPolicy)
 *
 * @param src: image data. shape = (indices, y, x)
 * @param constants: correction constants, which has the same shape as src.
 */
template <typename Policy, typename E, EnableIf<E, IsImageArray> = false>
inline void correctImageData(E& src, const E& constants)
{
  auto shape = src.shape();

  checkShape(shape, constants.shape(), "data and constants have different shapes");

#if defined(FOAM_WITH_TBB)
  tbb::parallel_for(tbb::blocked_range3d<int>(0, shape[0], 0, shape[1], 0, shape[2]),
    [&src, &constants] (const tbb::blocked_range3d<int> &block)
    {
      for(int i=block.pages().begin(); i != block.pages().end(); ++i)
      {
        for(int j=block.rows().begin(); j != block.rows().end(); ++j)
        {
          for(int k=block.cols().begin(); k != block.cols().end(); ++k)
          {
#else
      for (size_t i = 0; i < shape[0]; ++i)
      {
        for (size_t j = 0; j < shape[1]; ++j)
        {
          for (size_t k = 0; k < shape[2]; ++k)
          {
#endif
            src(i, j, k) = Policy::correct(src(i, j, k), constants(i, j, k));
          }
        }
      }
#if defined(FOAM_WITH_TBB)
    }
  );
#endif
}

/**
* Inplace apply either gain or offset correct for an image.
*
* @tparam Policy: correction policy (OffsetPolicy or GainPolicy)
*
* @param src: image data. shape = (y, x)
* @param constants: correction constants, which has the same shape as src.
*/
template <typename Policy, typename E, EnableIf<E, IsImage> = false>
inline void correctImageData(E& src, const E& constants)
{
  auto shape = src.shape();

  checkShape(shape, constants.shape(), "data and constants have different shapes");

  for (size_t j = 0; j < shape[0]; ++j)
  {
    for (size_t k = 0; k < shape[1]; ++k)
    {
      src(j, k) = Policy::correct(src(j, k), constants(j, k));
    }
  }
}

/**
* Inplace apply both gain and offset correct for an array of images.
*
* @param src: image data. shape = (indices, y, x)
* @param gain: gain correction constants, which has the same shape as src.
* @param offset: offset correction constants, which has the same shape as src.
*/
template <typename E, EnableIf<E, IsImageArray> = false>
inline void correctImageData(E& src, const E& gain, const E& offset)
{
  auto shape = src.shape();

  checkShape(shape, gain.shape(), "data and gain constants have different shapes");
  checkShape(shape, offset.shape(), "data and offset constants have different shapes");

#if defined(FOAM_WITH_TBB)
  tbb::parallel_for(tbb::blocked_range3d<int>(0, shape[0], 0, shape[1], 0, shape[2]),
    [&src, &gain, &offset] (const tbb::blocked_range3d<int> &block)
    {
      for(int i=block.pages().begin(); i != block.pages().end(); ++i)
      {
        for(int j=block.rows().begin(); j != block.rows().end(); ++j)
        {
          for(int k=block.cols().begin(); k != block.cols().end(); ++k)
          {
#else
  for (size_t i = 0; i < shape[0]; ++i)
    {
      for (size_t j = 0; j < shape[1]; ++j)
      {
        for (size_t k = 0; k < shape[2]; ++k)
        {
#endif
          src(i, j, k) = gain(i, j, k) * (src(i, j, k) - offset(i, j, k));
        }
      }
    }
#if defined(FOAM_WITH_TBB)
    }
  );
#endif
}

/**
* Inplace apply both gain and offset correct for an image.
*
* @param src: image data. shape = (y, x)
* @param gain: gain correction constants, which has the same shape as src.
* @param offset: offset correction constants, which has the same shape as src.
*/
template <typename E, EnableIf<E, IsImage> = false>
inline void correctImageData(E& src, const E& gain, const E& offset)
{
  auto shape = src.shape();

  checkShape(shape, gain.shape(), "data and gain constants have different shapes");
  checkShape(shape, offset.shape(), "data and offset constants have different shapes");

  for (size_t j = 0; j < shape[0]; ++j)
  {
    for (size_t k = 0; k < shape[1]; ++k)
    {
      src(j, k) = gain(j, k) * (src(j, k) - offset(j, k));
    }
  }
}

} // foam

#endif //EXTRA_FOAM_IMAGE_PROC_H
