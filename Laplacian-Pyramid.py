import numpy as np
import matplotlib.pyplot as plt
from scipy import ndimage
import cv2
import imageio

def create_filter():
      # create a  Binomial (5-tap) filter
      kernel = (1.0/256)*np.array([[1, 4, 6, 4, 1],
                             [4, 16, 24, 16, 4],
                             [6, 24, 36, 24, 6],
                             [4, 16, 24, 16, 4],
                             [1, 4, 6, 4, 1]])
      plt.title('Binomial Filter Kernel')
      plt.imshow(kernel)
      plt.show()
      return kernel

class Laplacian_Blend():
      def __init__(self):
            #权重核 weight kernel
            self.kernel = (1.0/256)*np.array([
                              [1, 4, 6, 4, 1],
                              [4, 16, 24, 16, 4],
                              [6, 24, 36, 24, 6],
                              [4, 16, 24, 16, 4],
                              [1, 4, 6, 4, 1]])

      def interpolate(self,image):  #插值（上采样），上采样率 = 2
            image_up = np.zeros((2*image.shape[0], 2*image.shape[1]))
            image_up[::2, ::2] = image  #每隔一个像素插入一个0：零填充
            # 由于内核有单位面积，因此需要扩大图片；长度和宽度增加两倍，因此面积增加4倍
            return ndimage.filters.convolve(image_up, 4*self.kernel, mode='constant') #低通滤波，去除插值带来的异常
            #输入图像，卷积核，处理边界外数组的方式

      def decimate(self,image):    #信号抽取（下采样+平滑滤波），下采样率 = 2
            image_blur = ndimage.filters.convolve(image, self.kernel, mode='constant')  #平滑滤波
            return image_blur[::2, ::2]  

      def buildPyramids(self,image):  #构建高斯金字塔和拉普拉斯金字塔
            #image为原比例的原图,是金字塔的第一层
            #初始化金字塔
            G = [image, ]   #高斯金字塔
            L = []          #拉普拉斯金字塔
            while image.shape[0] >= 2 and image.shape[1] >= 2:  #将高斯金字塔的深度构建到最大
                  image = self.decimate(image)  #信号抽取（下采样+平滑滤波）
                  G.append(image)  
            for i in range(len(G)-1):    #构建拉普拉斯金字塔
                  L.append(G[i] - self.interpolate(G[i+1])) #第i级的拉普拉斯图像 = 第i级的高斯图像 - （上采样第i+1级的高斯图像）
            return G[:-1], L  #[G,L] = 金字塔(图像)

      def pyramidBlending(self, A, B, mask):  #结合高斯金字塔和拉普拉斯金字塔
            [GA, LA] = self.buildPyramids(A)  #构建A图和B图的高斯金字塔和拉普拉斯金字塔
            [GB ,LB] = self.buildPyramids(B)
            [Gmask, LMask] = self.buildPyramids(mask)  #构建蒙版金字塔（蒙版表示像素来自左边还是右边）
            # 方程: LS(i, j) = GR(I, j)*LA(I, j) + (1-GR(I, j))* LB(I, j)
            blend = []
            for i in range(len(LA)):
                  #确保颜色在255里
                  LS = Gmask[i]/255*LA[i] + (1-Gmask[i]/255)*LB[i]  #以Gmask节点为权重，由LA和LB构建一个合成的金字塔LS
                  blend.append(LS)
            return blend   #最终的合成拉普拉斯金字塔

      def reconstruct(self,pyramid):  #重构金字塔+上采样+与每个级别相加
            reversePyramid = pyramid[::-1]   #从最后一层金字塔开始操作，因此倒转金字塔次序
            stack = reversePyramid[0]   
            for i in range(1, len(reversePyramid)):  #从第二个索引开始
                  stack = self.interpolate(stack) + reversePyramid[i] #上采样，对倒合成金字塔进行加法
            return stack   #返回最终已混合好的原比例的图

      def colorBlending(self, img1, img2, mask, filename):    #图像颜色混合 RGB
            img1R,img1G,img1B = cv2.split(img1) # 分成3种基本颜色
            img2R,img2G,img2B = cv2.split(img2)
            LSR = self.pyramidBlending(img1R, img2R, mask)  #分别对两个图像的三个颜色构建各自的合成拉普拉斯金字塔
            LSG = self.pyramidBlending(img1G, img2G, mask)
            LSB = self.pyramidBlending(img1B, img2B, mask)
            blendedR = self.reconstruct(LSR)  #重构
            blendedG = self.reconstruct(LSG)
            blendedB = self.reconstruct(LSB)
            output = cv2.merge((blendedR,blendedG,blendedB))  #叠加三种颜色已混合好的原比例图
            imageio.imsave(filename, output)  #保存图片
            return 

def BlendImage(ImageA,ImageB,Mask,result_dir):
      imgA = imageio.imread(ImageA)
      imgB = imageio.imread(ImageB)
      mask = cv2.imread(Mask, 0)
      l = Laplacian_Blend()
      l.colorBlending(imgA,imgB,mask,result_dir)
      output = imageio.imread(result_dir)
      return imgA, imgB, mask, output

def resize_image(img):
      image = imageio.imread(img)
      image.thumbnail((512, 512))
      image.save(img)

def getFigure(ImageA,ImageB,mask,output1,output2):
      fig, axarr = plt.subplots(2,2,constrained_layout=True)
      axarr[0,0].title.set_text('Original Image1')
      axarr[0,1].title.set_text('Original Image2')
      axarr[1,0].title.set_text('Image1 + Image2')
      axarr[1,1].title.set_text('Image2 + Image1')
      axarr[0,0].imshow(ImageA)
      axarr[0,1].imshow(ImageB)
      axarr[1,0].imshow(output2)
      axarr[1,1].imshow(output1)
      fig.tight_layout(pad=1.0)
      fig.suptitle('Mask '+str(mask))
      plt.show()


if __name__ == '__main__':
      mask_ls = ['images/mask.jpg','images/mask2.jpeg','images/mask3.jpg']
      img_ls = [  ['images/men1.jpg','images/men2.jpg'],
                  ['images/woman1.jpg','images/woman4.jpg'],
                  ['images/woman5.jpg','images/woman6.jpg'],
                  ['images/mountain1.jpg','images/mountain2.jpg'],
                  ['images/apple.jpg','images/orange.jpg']]
      create_filter()
      num = 1
      for img in img_ls:
            for i in range(len(mask_ls)):
                  imgA, imgB, mask, output1 = BlendImage(img[1], img[0], mask_ls[i], 'result/finalblend'+str(num)+'.png')
                  num += 1
                  m,n, mask, output2 = BlendImage(img[0], img[1], mask_ls[i], 'result/finalblend'+str(num)+'.png')
                  num += 1
                  getFigure(imgA,imgB,i+1,output1,output2)








